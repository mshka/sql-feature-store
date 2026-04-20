# sql-feature-store

[![CI](https://github.com/mshka/sql-feature-store/actions/workflows/ci.yml/badge.svg)](https://github.com/mshka/sql-feature-store/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)

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

## Install

```bash
pip install sql-feature-store
```

Requires Python `>=3.10,<3.13`.

## Quickstart

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

df = pd.DataFrame({"user_id": [1, 2, 3], "country": ["US", "UK", None]})
store.write("users", data_frame=df, write_option="replace")

result = store.read("select * from predictions.users")
# >>> result
#    user_id country
# 0        1      US
# 1        2      UK
# 2        3    None
```

Credentials are passed in directly — sourcing them (env vars, AWS Secrets
Manager, Vault, etc.) is the caller's responsibility.

## Documentation

Full API usage — chunked reads, write modes, indexes, `ON CONFLICT DO UPDATE`
upserts, automatic column migration, and pytest fixtures — lives in
[`docs/usage.md`](docs/usage.md).

## Contributing

Bug reports, feature requests, and pull requests are welcome. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup and the PR workflow,
and [`CHANGELOG.md`](CHANGELOG.md) for release notes.

## Layout

```
sql-feature-store/
├── pyproject.toml
├── .pre-commit-config.yaml
├── docs/
│   └── usage.md
├── src/sql_feature_store/
│   ├── __init__.py
│   ├── config.py              # PostgresConfig dataclass
│   └── store.py               # FeatureStore
└── tests/
    ├── conftest.py
    ├── postgres_db_utils.py
    └── feature_store_test.py
```

## License

Released under the [MIT License](LICENSE).
