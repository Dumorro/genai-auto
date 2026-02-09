# Contributing to GenAI Auto

First off, thank you for considering contributing to GenAI Auto! 🎉

## Code of Conduct

Be respectful, inclusive, and constructive. That's it.

## How Can I Contribute?

### Reporting Bugs

**Before submitting a bug report:**
- Check existing [issues](https://github.com/Dumorro/genai-auto/issues)
- Try to reproduce with latest version
- Gather relevant information (logs, environment, steps to reproduce)

**How to submit a bug report:**
1. Use the issue template (if available)
2. Include a clear title and description
3. Provide steps to reproduce
4. Share expected vs actual behavior
5. Include logs, screenshots, or error messages
6. Mention your environment (OS, Python version, Docker version)

### Suggesting Features

**Before suggesting a feature:**
- Check if it's already been suggested
- Consider if it aligns with project goals
- Think about how it benefits the majority of users

**How to suggest a feature:**
1. Open an issue with title: `[Feature Request] Your Feature Name`
2. Describe the problem it solves
3. Explain your proposed solution
4. Provide examples or mockups (if applicable)
5. Mention alternative solutions you've considered

### Pull Requests

**Good first issues:**
- Documentation improvements
- Test coverage
- Bug fixes
- Performance optimizations

**Before submitting a PR:**
1. Fork the repository
2. Create a branch from `main`: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Add tests (if applicable)
5. Update documentation
6. Run linting and tests
7. Commit with clear messages (see [Commit Guidelines](#commit-guidelines))

**PR checklist:**
- [ ] Code follows project style
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No breaking changes (or clearly documented)
- [ ] Branch is up-to-date with `main`

## Development Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/genai-auto.git
cd genai-auto

# Add upstream remote
git remote add upstream https://github.com/Dumorro/genai-auto.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # Includes dev dependencies (pytest, black, ruff, mypy)

# Copy environment template
cp .env.example .env

# Start services
docker-compose up -d postgres redis

# Run API
uvicorn src.api.main:app --reload
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=html

# Specific test file
pytest tests/test_api.py -v

# Watch mode (requires pytest-watch)
ptw tests/ -- -v
```

### Code Style

We use:
- **Black** for formatting
- **Ruff** for linting
- **mypy** for type checking

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

**Pre-commit hook (recommended):**
```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
genai-auto/
├── src/                    # Source code
│   ├── api/                # FastAPI app
│   ├── agents/             # LangGraph agents
│   ├── rag/                # RAG pipeline
│   └── storage/            # Database models
├── tests/                  # Test files (mirror src/ structure)
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── docker/                 # Docker configs (if needed)
```

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/).

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Test changes
- `chore`: Build, tooling, dependencies

**Examples:**
```
feat(metrics): add user feedback tracking API

Implement POST /api/v1/feedback endpoint for collecting
thumbs up/down ratings on chat responses.

Closes #42
```

```
fix(rag): correct similarity score calculation

The previous formula didn't normalize embeddings properly,
causing inconsistent similarity scores.
```

```
docs(readme): update Quick Start with monitoring setup

Add instructions for launching Prometheus + Grafana
alongside the main services.
```

## Branch Naming

- `feature/short-description` - New features
- `fix/short-description` - Bug fixes
- `docs/short-description` - Documentation
- `refactor/short-description` - Refactoring
- `test/short-description` - Tests

## Testing Guidelines

### Writing Tests

**Structure:**
```python
# tests/test_module.py
import pytest
from src.module import function

def test_function_happy_path():
    """Test function with valid input."""
    result = function(valid_input)
    assert result == expected_output

def test_function_edge_case():
    """Test function with edge case."""
    result = function(edge_case_input)
    assert result == expected_edge_output

def test_function_invalid_input():
    """Test function with invalid input."""
    with pytest.raises(ValueError):
        function(invalid_input)
```

**Best practices:**
- One assertion per test (when possible)
- Use descriptive test names
- Test happy path, edge cases, and error conditions
- Use fixtures for common setup
- Mock external dependencies

### Test Coverage

Aim for:
- **80%+ overall coverage**
- **100% coverage** for critical paths (auth, payments, data integrity)
- **No coverage decrease** in PRs (CI will check)

## Documentation Guidelines

### Code Documentation

**Docstrings (Google style):**
```python
def calculate_cost(model: str, tokens: int) -> float:
    """
    Calculate LLM cost for given model and token count.
    
    Args:
        model: Model identifier (e.g., "gpt-4")
        tokens: Number of tokens used
    
    Returns:
        Cost in dollars
    
    Raises:
        ValueError: If model is not recognized
    
    Example:
        >>> calculate_cost("gpt-4", 1000)
        0.03
    """
```

### Markdown Documentation

- Use clear headings
- Include code examples
- Add links to related docs
- Keep language simple and direct
- Use tables for comparisons
- Add diagrams (Mermaid preferred)

## Release Process

(For maintainers)

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml` (if using)
3. Create release branch: `release/v1.2.3`
4. Run full test suite
5. Merge to `main`
6. Tag release: `git tag v1.2.3`
7. Push tags: `git push --tags`
8. Create GitHub release with notes

## Getting Help

- 💬 **Questions**: Open a [Discussion](https://github.com/Dumorro/genai-auto/discussions)
- 🐛 **Bugs**: Open an [Issue](https://github.com/Dumorro/genai-auto/issues)
- 📧 **Email**: tfcoelho@msn.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to GenAI Auto! 🚀
