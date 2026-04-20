# sql-feature-store

Lightweight online feature store backed by a SQL database, with a pandas API.
Currently implemented for PostgreSQL; designed so other SQL backends (e.g.
MySQL) can be added later.

## What it does

- Parses a `DataFrame` into appropriate column types
- Creates the destination table if it does not exist
- Migrates the table by adding new columns when the `DataFrame` has extra ones
- Supports write modes: `fail`, `replace`, `append`
- Supports index creation and `ON CONFLICT DO UPDATE` upserts
- Reads via SQL (optionally in chunks)

## Usage

```python
import pandas as pd
from sql_feature_store import FeatureStore, PostgresConfig

config = PostgresConfig(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="postgres",
)
store = FeatureStore(config=config)

df = pd.DataFrame({"worker_id": [1, 2, 3], "city": ["London", "Paris", None]})
store.write("shifts", data_frame=df, write_option="replace")

result = store.read("select * from predictions.shifts")
```

Credentials are passed in directly — sourcing them (env vars, AWS Secrets
Manager, Vault, etc.) is the caller's responsibility.

## Requirements

- Python `>=3.10,<3.13`
- PostgreSQL (required by `pytest-postgresql`, which spawns a real `postgres` process for the integration tests)
- [Poetry](https://python-poetry.org/) for dependency management
- [pre-commit](https://pre-commit.com/) for git hooks

### macOS (Homebrew)

```bash
brew install python@3.12 postgresql@16 poetry pre-commit
```

### Linux (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql pipx
pipx ensurepath
pipx install poetry
pipx install pre-commit
```

On Fedora / RHEL, substitute `apt` with `dnf` and the package names accordingly
(`python3.12`, `postgresql-server`, `pipx`).

### Install

```bash
poetry install          # runtime + dev deps
pre-commit install      # set up the git hook (run once per clone)
```

Python-level dependencies are declared in `pyproject.toml` and locked in `poetry.lock`.

## Layout

```
sql-feature-store/
├── pyproject.toml
├── .pre-commit-config.yaml
├── src/sql_feature_store/
│   ├── __init__.py
│   ├── config.py              # PostgresConfig dataclass
│   └── store.py               # FeatureStore
└── tests/
    ├── conftest.py
    ├── postgres_db_utils.py
    └── feature_store_test.py
```
