# Backend

Python, FastAPI (dev only), AWS Lambda (prod).

## Commands

- **Tests**: `uv run pytest`
- **Lint**: `uv run ruff check .`
- **Type check**: `uv run mypy .`

## Conventions

- All Lambda handlers follow the pattern in `src/app/dispatcher.py`: single `handler(event, context)` entry point.
- Use `get_method` and `require_session` from `session_guard.py` (Lambda Layer) — do not reimplement.
- Domain modules (`*/domain.py`) are pure: no I/O, no timestamps sourced internally, no UUID generation.
- Repository modules (`*/repository.py`) own all DynamoDB access.
- Handler modules (`*/handler.py`) are the boundary: read env, verify session, call domain + repo, return HTTP dicts.
- DynamoDB tests use `moto` (`mock_aws`). The shared `table` fixture lives in `tests/conftest.py`.
