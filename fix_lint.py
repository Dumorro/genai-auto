#!/usr/bin/env python3
"""
Quick script to fix common linting errors.
"""

import re
from pathlib import Path

# Files and unused imports to remove
fixes = {
    "src/agents/maintenance/agent.py": ["timedelta"],
    "src/agents/troubleshoot/agent.py": ["ChatPromptTemplate"],
    "src/api/auth/jwt_auth.py": ["get_db"],
    "src/api/cache.py": ["Any", "wraps"],
    "src/api/observability.py": ["token_tracker"],
    "src/api/pii.py": ["Optional"],
    "src/api/routes/chat_example.py": ["Depends"],
    "src/api/routes/evaluation.py": ["EvaluationReport"],
    "src/api/routes/metrics_routes.py": ["HTTPException", "Depends"],
    "src/api/routes/websocket.py": ["json"],
    "src/evaluation/dataset.py": ["Path"],
    "src/evaluation/metrics.py": ["Dict", "Any"],
    "src/evaluation/runner.py": ["Optional", "Any", "Path"],
    "src/experiments/ab_testing.py": ["Callable", "timedelta"],
    "src/observability/model_drift.py": ["time"],
    "src/orchestrator/graph.py": ["AIMessage"],
    "src/rag/embeddings.py": ["Optional", "asyncio"],
    "src/rag/pipeline.py": ["Optional", "BinaryIO", "Path"],
    "src/rag/vectorstore.py": ["Optional"],
    "src/storage/models.py": ["Optional"],
    "tests/integration/test_e2e_flow.py": ["Dict", "Any"],
    "tests/integration/test_websocket.py": ["json"],
    "tests/test_auth.py": ["pytest"],
}

# Fix unused variables (e -> _e)
unused_vars = [
    "src/api/cache_service.py",
    "src/api/metrics.py",
    "src/api/routes/chat_example.py",
    "src/evaluation/metrics.py",
    "src/experiments/ab_testing.py",
    "tests/integration/test_websocket.py",
]

for file_path, imports_to_remove in fixes.items():
    path = Path(file_path)
    if not path.exists():
        continue
    
    content = path.read_text()
    
    for import_name in imports_to_remove:
        # Remove from "from X import Y, Z" lines
        content = re.sub(
            rf',\s*{import_name}\b',
            '',
            content
        )
        content = re.sub(
            rf'\b{import_name}\s*,',
            '',
            content
        )
        # Remove standalone import
        content = re.sub(
            rf'^from .* import {import_name}\n',
            '',
            content,
            flags=re.MULTILINE
        )
        content = re.sub(
            rf'^import {import_name}\n',
            '',
            content,
            flags=re.MULTILINE
        )
    
    path.write_text(content)
    print(f"✅ Fixed {file_path}")

# Fix unused variables (e -> _)
for file_path in unused_vars:
    path = Path(file_path)
    if not path.exists():
        continue
    
    content = path.read_text()
    
    # Replace "except Exception as e:" with "except Exception:"
    content = re.sub(
        r'except\s+\w+\s+as\s+e:',
        'except Exception:',
        content
    )
    
    # Replace unused variables with _
    content = re.sub(r'\b(context|queries)\s*=', r'_\1 =', content)
    
    path.write_text(content)
    print(f"✅ Fixed unused vars in {file_path}")

print("\n✅ All fixes applied!")
