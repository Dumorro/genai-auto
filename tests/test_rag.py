"""RAG pipeline tests."""

import pytest
from src.rag.chunker import (
    DocumentChunker,
    ChunkerConfig,
    ChunkingStrategy,
    auto_detect_strategy,
)


class TestDocumentChunker:
    """Document chunker tests."""

    def test_default_chunking(self):
        """Test default recursive chunking."""
        chunker = DocumentChunker()
        text = "This is a test document. " * 100

        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        assert all(len(c.content) <= 1200 for c in chunks)  # chunk_size + some overlap

    def test_custom_chunk_size(self):
        """Test chunking with custom size."""
        config = ChunkerConfig(chunk_size=500, chunk_overlap=50)
        chunker = DocumentChunker(config)
        text = "This is a test document. " * 100

        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        # Most chunks should be around the configured size
        avg_size = sum(len(c.content) for c in chunks) / len(chunks)
        assert avg_size < 600

    def test_semantic_chunking(self):
        """Test semantic paragraph-based chunking."""
        chunker = DocumentChunker()
        text = """First paragraph with some content.

Second paragraph with different content.

Third paragraph with more information."""

        chunks = chunker.chunk(text, strategy=ChunkingStrategy.SEMANTIC)

        assert len(chunks) >= 1

    def test_fixed_chunking(self):
        """Test fixed-size chunking."""
        config = ChunkerConfig(chunk_size=100, chunk_overlap=10)
        chunker = DocumentChunker(config)
        text = "A" * 500

        chunks = chunker.chunk(text, strategy=ChunkingStrategy.FIXED)

        assert len(chunks) > 1

    def test_metadata_propagation(self):
        """Test that metadata is included in chunks."""
        chunker = DocumentChunker()
        text = "Test content " * 50
        metadata = {"source": "test.txt", "author": "Test"}

        chunks = chunker.chunk(text, metadata=metadata)

        assert all("source" in c.metadata for c in chunks)
        assert all(c.metadata["source"] == "test.txt" for c in chunks)

    def test_empty_text(self):
        """Test chunking empty text."""
        chunker = DocumentChunker()
        chunks = chunker.chunk("")
        assert len(chunks) == 0


class TestAutoDetectStrategy:
    """Strategy auto-detection tests."""

    def test_detect_markdown(self):
        """Test detection of markdown content."""
        content = """# Header

Some content here.

## Subheader

More content."""

        strategy = auto_detect_strategy(content)
        assert strategy == ChunkingStrategy.MARKDOWN

    def test_detect_markdown_by_filename(self):
        """Test detection by filename extension."""
        strategy = auto_detect_strategy("Regular text", "document.md")
        assert strategy == ChunkingStrategy.MARKDOWN

    def test_detect_plain_text(self):
        """Test detection of plain text."""
        content = "This is just regular plain text without any special formatting."
        strategy = auto_detect_strategy(content, "document.txt")
        assert strategy == ChunkingStrategy.RECURSIVE


class TestChunkingStrategies:
    """Test different chunking strategies produce valid output."""

    @pytest.fixture
    def sample_text(self):
        return """
# Vehicle Specifications

## Engine
The engine is a 2.0L turbocharged four-cylinder.

### Power Output
- Horsepower: 250 hp
- Torque: 280 lb-ft

## Transmission
6-speed automatic transmission with manual mode.

## Dimensions
- Length: 185 inches
- Width: 73 inches
- Height: 57 inches
"""

    def test_all_strategies_produce_chunks(self, sample_text):
        """Test that all strategies produce valid chunks."""
        chunker = DocumentChunker()

        for strategy in ChunkingStrategy:
            chunks = chunker.chunk(sample_text, strategy=strategy)
            assert len(chunks) > 0, f"Strategy {strategy} produced no chunks"
            assert all(c.content for c in chunks), f"Strategy {strategy} produced empty chunks"
