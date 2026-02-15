# AGENTS.md

AI coding agents working on this repository should follow these guidelines.

## Build Commands

```bash
# Install dependencies
make dev                    # Install with dev dependencies
make install                # Production only

# Run tests
make test                   # All tests with coverage (80% minimum)
make test-unit              # Unit tests only
make test-integration       # Integration tests only
pytest tests/unit/llm/test_openai.py -v   # Single test file
pytest tests/unit/config/test_settings.py::TestParseModelString -v  # Single test class
pytest -k "test_openai" -v  # Run tests matching pattern

# Code quality
make lint                   # Ruff linter
make format                 # Ruff formatter
make typecheck              # MyPy type checking
```

## Project Architecture

```
ken/
├── src/
│   ├── config/           # Pydantic settings from .env
│   ├── llm/              # LLM provider abstraction
│   │   ├── base.py       # Abstract provider class
│   │   ├── factory.py    # Provider factory & auto-detection
│   │   ├── errors.py     # LLM-specific exceptions
│   │   └── providers/    # 23 provider implementations
│   ├── observability/    # Langfuse tracing (optional)
│   ├── storage/          # Postgres + per-user storage
│   ├── api/              # FastAPI endpoints
│   ├── telegram/         # Telegram bot
│   └── cli/              # Typer CLI
├── tests/
│   ├── unit/             # Fast, isolated tests
│   ├── integration/      # Database/API tests
│   └── conftest.py       # Shared fixtures
└── docker/               # Docker configuration
```

## Code Style

### Imports
```python
# Standard library first
from __future__ import annotations
from pathlib import Path
from typing import Any

# Third-party
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

# Local imports last
from src.config.settings import get_settings
from src.llm.errors import LLMError
```

### Type Hints
- Always use type hints for function parameters and return types
- Use `from __future__ import annotations` for forward references
- Prefer `list[str]` over `List[str]`, `dict[str, Any]` over `Dict[str, Any]`

### Error Handling
```python
# Use custom exceptions from src.llm.errors
from src.llm.errors import LLMConfigurationError, LLMProviderNotFoundError

def create_chat_model(model: str) -> ChatOpenAI:
    if not self.api_key:
        raise LLMConfigurationError(
            "OpenAI API key is required",
            provider="openai",
        )
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `OpenAIProvider`)
- Functions/variables: `snake_case` (e.g., `get_llm`, `user_id`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MODEL_PREFIX_TO_PROVIDER`)
- Private methods: `_leading_underscore`
- Type variables: `T` or `TModel`

### Pydantic Models
```python
class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    model: str | None = Field(None, description="Model in format provider/model-name")
    temperature: float = Field(0.7, ge=0, le=2)
```

## Model Selection

Users specify models as `provider/model-name`:
```python
# Examples:
# - openai/gpt-4o
# - anthropic/claude-3-5-sonnet-20241022
# - groq/llama-3.3-70b-versatile

from src.llm import get_llm

llm = get_llm(provider="openai", model="gpt-4o")
llm = get_llm(model="openai/gpt-4o")  # Auto-detects provider

# Default and summarization models from settings
from src.llm import get_default_llm, get_summarization_llm
```

## Storage

Per-user storage structure:
```
/data/users/{user_id}/
├── .auth/
│   ├── google.json
│   └── microsoft.json
└── projects/          # User-managed
```

```python
from src.storage import UserStorage

storage = UserStorage(user_id="user-123", base_path=Path("/data"))
storage.ensure_user_dir()
storage.save_google_auth(tokens)
db_path = storage.create_sqlite("projects/my-project/data.db")
lance_path = storage.create_lancedb("projects/my-project/vectors.lance")
```

## Testing Guidelines

### Unit Tests
- Mock external dependencies (LLM APIs, databases)
- Test one thing per test function
- Use fixtures from `conftest.py`

```python
def test_get_llm_raises_for_unknown_provider() -> None:
    with pytest.raises(LLMProviderNotFoundError):
        get_llm(provider="unknown", model="model")
```

### Integration Tests
- Use real database connections in CI
- Test edge cases and error scenarios
- Clean up resources after tests

## Docker

```bash
# Development (hot reload)
make docker-dev

# Production
make docker-up

# View logs
make docker-logs

# Stop
make docker-down
```

## Configuration

All configuration via environment variables in `.env`:
- `DEFAULT_MODEL=openai/gpt-4o` - Main chat model
- `SUMMARIZATION_MODEL=openai/gpt-4o-mini` - Summarization tasks
- `LANGFUSE_ENABLED=false` - Toggle Langfuse tracing
- `TELEGRAM_ENABLED=false` - Toggle Telegram bot

## When Adding New Features

1. Write failing tests first (TDD)
2. Implement minimum code to pass
3. Add edge case tests
4. Run `make lint format test` before committing
5. Ensure 80%+ test coverage

## Common Patterns

### Adding a New LLM Provider

1. Create `src/llm/providers/new_provider.py`:
```python
class NewProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "new_provider"

    def is_available(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_settings(cls, settings: Settings) -> NewProvider:
        return cls(api_key=settings.llm.new_provider_api_key)

    def create_chat_model(self, model: str, **kwargs) -> BaseChatModel:
        # Return LangChain-compatible chat model
        pass
```

2. Add to `src/llm/providers/__init__.py`
3. Add to `src/llm/factory.py` `_load_providers()`
4. Add env key to `src/config/settings.py`
5. Add to `.env.example`
6. Write tests in `tests/unit/llm/providers/test_new_provider.py`
