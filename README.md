# sql-feature-store

[![CI](https://github.com/mshka/sql-feature-store/actions/workflows/ci.yml/badge.svg)](https://github.com/mshka/sql-feature-store/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/mshka/sql-feature-store/branch/main/graph/badge.svg)](https://codecov.io/gh/mshka/sql-feature-store)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

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

Requires Python `>=3.10,<3.14`.

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

## Testing your own code

`sql-feature-store` ships a pytest plugin so your tests can hit a real
PostgreSQL without wiring up fixtures from scratch. Install the `testing`
extra:

```bash
pip install sql-feature-store[testing]
```

Three fixtures are auto-discovered:

- `sql_feature_store_postgres_proc` — a Postgres process (spawned via
  `pytest-postgresql`, or an external DB when `SFS_POSTGRES_HOST` is set).
- `sql_feature_store_config` — a `PostgresConfig` with a fresh random
  `write_schema` per test, dropped on teardown.
- `sql_feature_store_fixture` — a ready `FeatureStore` pointed at that
  schema.

```python
import pandas as pd

def test_round_trip(sql_feature_store_fixture, sql_feature_store_config):
    store = sql_feature_store_fixture
    schema = sql_feature_store_config.write_schema

    store.write("users", data_frame=pd.DataFrame({"user_id": [1, 2, 3]}))
    result = store.read(f"select * from {schema}.users")
    assert len(result) == 3
```

See [`docs/usage.md`](docs/usage.md#testing-with-pytest) for the full
fixture reference and the external-database env vars.

## Documentation

- [`docs/usage.md`](docs/usage.md) — full API reference: chunked reads, write
  modes, indexes, `ON CONFLICT DO UPDATE` upserts, automatic column migration,
  and the pytest fixture reference.
- [`docs/roadmap.md`](docs/roadmap.md) — what's coming next, organised by
  target version (online feature store → multi-dialect → offline → 1.0).

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
│   ├── usage.md
│   └── roadmap.md
├── src/sql_feature_store/
│   ├── __init__.py
│   ├── config.py              # PostgresConfig dataclass
│   ├── store.py               # FeatureStore
│   └── testing/               # pytest plugin shipped as [testing] extra
│       └── plugin.py          # fixtures: _postgres_proc, _config, _fixture
└── tests/
    └── integration/           # one test file per feature area
```

## License

Released under the [MIT License](LICENSE).
