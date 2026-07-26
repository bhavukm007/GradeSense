# GradeSenseAI Backend

The backend provides snapshot intelligence, sequential forecasting, constraint-safe intervention
support, real-time streaming, model governance, observability, audit, configuration, and exports.

Runtime startup requires the supplied datasets and pre-trained model artifacts and does not
generate or train automatically. The explicit `/dataset/regenerate` compatibility endpoint and
offline scripts are retained for controlled development and experimentation.

## Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

## Quality

```bash
python -m pytest
python -m ruff check app tests
python -m black --check app tests
```

Module boundaries:

- `api`: HTTP/WebSocket transport
- `schemas`: validated public contracts
- `services`: intelligence and operational behavior
- `models`: relational persistence
- `database`: engine/session lifecycle
- `config`: typed environment settings
- `core`: logging and exception handling

See the repository [README](../README.md), [API reference](../docs/API_REFERENCE.md), and
[system architecture](../docs/SYSTEM_ARCHITECTURE.md).
