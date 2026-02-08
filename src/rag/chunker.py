"""Document chunking strategies for RAG."""

import re
from typing import List, Optional
from enum import Enum

import structlog
from pydantic import BaseModel, Field
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

logger = structlog.get_logger()


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    
    RECURSIVE = "recursive"  # General purpose, respects sentence boundaries
    SEMANTIC = "semantic"    # Based on content meaning (paragraphs)
    MARKDOWN = "markdown"    # For markdown documents, respects headers
    FIXED = "fixed"          # Fixed size chunks


class DocumentChunk(BaseModel):
    """A chunk of document content."""
    
    content: str
    metadata: dict = Field(default_factory=dict)
    chunk_index: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ChunkerConfig(BaseModel):
    """Configuration for document chunking."""
    
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: List[str] = Field(
        default_factory=lambda: ["\n\n", "\n", ". ", " ", ""]
    )


class DocumentChunker:
    """Intelligent document chunking for RAG."""

    def __init__(self, config: ChunkerConfig = None):
        self.config = config or ChunkerConfig()

    def chunk(
        self,
        text: str,
        metadata: dict = None,
        strategy: ChunkingStrategy = None,
    ) -> List[DocumentChunk]:
        """Chunk a document into smaller pieces.
        
        Args:
            text: Document text to chunk
            metadata: Base metadata to include in all chunks
            strategy: Override default chunking strategy
            
        Returns:
            List of document chunks
        """
        strategy = strategy or self.config.strategy
        metadata = metadata or {}

        logger.info(
            "Chunking document",
            strategy=strategy.value,
            text_length=len(text),
            chunk_size=self.config.chunk_size,
        )

        if strategy == ChunkingStrategy.RECURSIVE:
            chunks = self._chunk_recursive(text)
        elif strategy == ChunkingStrategy.SEMANTIC:
            chunks = self._chunk_semantic(text)
        elif strategy == ChunkingStrategy.MARKDOWN:
            chunks = self._chunk_markdown(text)
        elif strategy == ChunkingStrategy.FIXED:
            chunks = self._chunk_fixed(text)
        else:
            chunks = self._chunk_recursive(text)

        # Build DocumentChunk objects
        result = []
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                content=chunk_text,
                metadata={
                    **metadata,
                    "chunk_strategy": strategy.value,
                    "chunk_size": self.config.chunk_size,
                },
                chunk_index=i,
            )
            result.append(chunk)

        logger.info(
            "Document chunked",
            total_chunks=len(result),
            avg_chunk_size=sum(len(c.content) for c in result) // max(len(result), 1),
        )

        return result

    def _chunk_recursive(self, text: str) -> List[str]:
        """Recursive character splitting with smart boundaries."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            length_function=len,
        )
        return splitter.split_text(text)

    def _chunk_semantic(self, text: str) -> List[str]:
        """Semantic chunking based on paragraphs and sections."""
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If adding this paragraph exceeds chunk size, save current and start new
            if len(current_chunk) + len(para) + 2 > self.config.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Handle overlap by including end of previous chunk
        if self.config.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_end = chunks[i-1][-self.config.chunk_overlap:]
                overlapped_chunks.append(prev_end + "\n\n" + chunks[i])
            chunks = overlapped_chunks
        
        return chunks

    def _chunk_markdown(self, text: str) -> List[str]:
        """Chunk markdown documents respecting header structure."""
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]
        
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
        )
        
        # First split by headers
        md_chunks = md_splitter.split_text(text)
        
        # Then apply recursive splitting to large chunks
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        
        final_chunks = []
        for doc in md_chunks:
            content = doc.page_content
            if len(content) > self.config.chunk_size:
                sub_chunks = recursive_splitter.split_text(content)
                # Prepend header context to each sub-chunk
                header_context = " > ".join(
                    f"{k}: {v}" for k, v in doc.metadata.items()
                )
                for sub in sub_chunks:
                    final_chunks.append(f"[{header_context}]\n{sub}")
            else:
                final_chunks.append(content)
        
        return final_chunks

    def _chunk_fixed(self, text: str) -> List[str]:
        """Simple fixed-size chunking."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.config.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.config.chunk_overlap
        
        return chunks


def auto_detect_strategy(content: str, filename: str = None) -> ChunkingStrategy:
    """Auto-detect the best chunking strategy based on content."""
    
    # Check filename extension
    if filename:
        if filename.endswith('.md'):
            return ChunkingStrategy.MARKDOWN
    
    # Check content for markdown indicators
    markdown_patterns = [
        r'^#{1,6}\s+',  # Headers
        r'^\*\*.*\*\*',  # Bold
        r'^\[.*\]\(.*\)',  # Links
        r'^```',  # Code blocks
    ]
    
    for pattern in markdown_patterns:
        if re.search(pattern, content, re.MULTILINE):
            return ChunkingStrategy.MARKDOWN
    
    # Default to recursive (most versatile)
    return ChunkingStrategy.RECURSIVE
