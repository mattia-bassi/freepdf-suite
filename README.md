# FreePDF Suite

A free, open-source, modular desktop PDF toolkit built with Python 3.11+ and Qt6.

## Project Layout

| Folder            | Purpose                                                    |
| ----------------- | ---------------------------------------------------------- |
| `core/`           | Core engine and shared services (PDF I/O, document model). |
| `modules/`        | Feature modules (merge, split, OCR, compress, etc.).       |
| `ui/`             | Qt6 user interface (windows, widgets, dialogs).            |
| `module-manager/` | Module discovery, registration, and lifecycle management.  |
| `docs/`           | User and developer documentation.                          |
| `tests/`          | Pytest test suite.                                         |
| `scripts/`        | Developer and build scripts.                               |
| `config/`         | Default configuration and schemas.                         |

## Requirements

- Python **3.11+**
- [Poetry](https://python-poetry.org/) for dependency management

## Getting Started

```bash
# Install dependencies (including dev tools)
poetry install

# Activate the virtual environment
poetry shell

# Run the test suite
poetry run pytest

# Format the codebase
poetry run black .

# Type-check
poetry run mypy .
```

## License

Released under the [MIT License](LICENSE).
