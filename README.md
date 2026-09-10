# Linux Bluetooth Audio Diagnostics

A Python CLI toolkit for collecting and analysing Linux Bluetooth audio state
across BlueZ, PipeWire, and related system services.

> Status: early development.

## Requirements

- Linux
- Python 3.13+

## Development setup

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install the project in editable mode with development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## CLI

Show CLI help:

```bash
bt-audio-diag --help
```

Show the installed application version:

```bash
bt-audio-diag --version
```

## Quality checks

Run the test suite:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

Check formatting:

```bash
ruff format --check .
```

Run static type checking:

```bash
mypy
```