# Usage

Full API reference and examples for `sql-feature-store`.

For installation, see the [README](../README.md).

## Contents

- [Connecting](#connecting)
- [Schema creation](#schema-creation)
- [Connection pool](#connection-pool)
- [Reading](#reading)
- [Feature views and entity-keyed reads](#feature-views-and-entity-keyed-reads)
- [Writing](#writing)
- [Indexes](#indexes)
- [Upserts (`ON CONFLICT DO UPDATE`)](#upserts-on-conflict-do-update)
- [Automatic column migration](#automatic-column-migration)
- [Table name validation](#table-name-validation)
- [Testing with pytest](#testing-with-pytest)

## Connecting

`FeatureStore` takes a `PostgresConfig` with connection parameters. Sourcing
those values (env vars, AWS Secrets Manager, Vault, etc.) is the caller's
responsibility — this library doesn't fetch or rotate credentials.

```python
from sql_feature_store import FeatureStore, PostgresConfig

config = PostgresConfig(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="postgres",
    write_schema="predictions",  # default: "predictions"
)

store = FeatureStore(config=config)
```

All writes go to `config.write_schema`. Reads use whatever schema is referenced
in the SQL you pass.

## Schema creation

By default, `write_schema` is created automatically on the first `write()` call
(`CREATE SCHEMA IF NOT EXISTS`). The check is memoised on the `FeatureStore`
instance, so subsequent writes skip it. This requires the connecting role to
have `CREATE` privilege on the database.

If the schema is managed externally (locked-down role, DBA-controlled
migrations, etc.), disable auto-creation and surface a clear error when the
schema is missing:

```python
config = PostgresConfig(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="postgres",
    create_schema_if_missing=False,
)
```

With the flag off, `write()` raises `sqlalchemy.exc.ProgrammingError` if
`write_schema` doesn't exist.

## Connection pool

The SQLAlchemy engine is created with connection pooling, `pool_pre_ping=True`,
and a `pool_recycle` to handle rotated/stale connections. All three knobs are
configurable:

```python
store = FeatureStore(
    config=config,
    pool_size=20,          # default
    max_overflow=10,       # default
    pool_recycle=1800,     # seconds, default
)
```

## Reading

### Simple read

Returns a single `DataFrame`:

```python
df = store.read("SELECT * FROM predictions.users LIMIT 5")
```

### Chunked read (recommended for large queries)

Pass `chunksize` to stream results as an iterator of `DataFrame`s:

```python
for chunk in store.read("SELECT * FROM predictions.users", chunksize=1000):
    process(chunk)
```

Under the hood this uses a server-side cursor (`stream_results=True`), so rows
aren't all loaded into memory at once.

## Feature views and entity-keyed reads

Feature views give you a small declarative wrapper over a table so callers can
look up rows by entity ID without writing SQL. The view itself is a 4-field
dataclass; the store does the query.

```python
from sql_feature_store import FeatureView

users_view = FeatureView(
    table="users",
    entity="user_id",
    features=["country", "age"],
    last_updated=None,  # optional freshness column; see Phase 1.4 in roadmap
)
```

`FeatureView` is frozen and has no engine, no SQL, and no registry — just a
declaration. The `read()` path is still available for everything that doesn't
fit this shape.

### `get_online_features`

Look up features for a list of entity IDs, in caller-supplied order:

```python
result = store.get_online_features(
    entity_ids=[1, 2, 3],
    view=users_view,
)
#         users.country  users.age
# user_id
# 1                  US         21
# 2                  US         34
# 3                  FR         47
```

Contract:

- One row per requested entity (modulo `on_missing`, below).
- Indexed by `view.entity`.
- Feature columns are renamed `{view.table}.{feature}` so multi-view merges
  (Phase 1.3) won't collide.
- Caller order is preserved.

### `on_missing`

Controls behaviour when a requested entity has no row in the table:

| Value | Behaviour |
|---|---|
| `"null"` *(default)* | Missing entities get a row of NaN values. |
| `"raise"` | Raises `KeyError` listing the missing entity IDs. |
| `"skip"` | Missing entities are dropped from the result. |

```python
store.get_online_features(entity_ids=[1, 999], view=users_view, on_missing="skip")
# returns just the row for user 1; 999 is dropped silently
```

### Inspecting the SQL

`get_online_features_sql` returns the exact SQL that `get_online_features`
would execute, with bind values inlined. No DB connection is opened — useful
for debugging, planning, or piping into `EXPLAIN`:

```python
print(store.get_online_features_sql(entity_ids=[1, 2], view=users_view))
# SELECT users.user_id, users.country, users.age
# FROM predictions.users
# WHERE users.user_id IN (1, 2)
```

### Read schema

By default reads target `config.write_schema`. Override per-call with
`read_schema=`:

```python
store.get_online_features(entity_ids=[1], view=users_view, read_schema="analytics")
```

### Caveats

- The view is assumed to have **at most one row per entity**. If the table can
  have duplicates, the result is undefined — enforce uniqueness at the schema
  level (a unique index helper is on the roadmap).
- For large `entity_ids` lists, the generated `IN (...)` clause grows linearly.
  This is intentional for now; revisit only if profiling shows it matters.

## Writing

```python
import pandas as pd

data = pd.DataFrame({
    "user_id": [1, 2, 3],
    "username": ["alice", "bob", "carol"],
    "country": ["US", "US", None],
})

store.write("users", data_frame=data, write_option="replace")
```

### Write options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `table_name` | `str` | — | Destination table. Written to `config.write_schema`. Validated against `^[a-z0-9_]+$`. |
| `data_frame` | `pd.DataFrame` | — | Data to write. |
| `write_option` | `"fail" \| "replace" \| "append"` | `"replace"` | Action if the table exists. See below. |
| `dtype_mapping` | `Dict[str, np.dtype]` | `None` | Override column types on table creation, e.g. `{"user_id": BigInteger}`. |
| `chunksize` | `int` | `1000` | Rows per batch when creating/replacing the table. |
| `with_indices` | `Dict` | `{}` | Indexes to create after write. See [Indexes](#indexes). |
| `on_conflict_do_update` | `Dict` | `{}` | Upsert clause for `append` mode. See [Upserts](#upserts-on-conflict-do-update). |

#### `write_option`

- `append` — insert into the existing table; auto-adds any new columns present
  in the `DataFrame`; runs as `INSERT ... ON CONFLICT DO NOTHING` unless
  `on_conflict_do_update` is provided.
- `replace` — drop and recreate the table with the current `DataFrame`.
- `fail` — raise if the table already exists.

If the table doesn't exist yet, `append` and `fail` both fall through to
creating it.

## Indexes

Pass `with_indices` to create one or more indexes after the write. The key is
the index name; the value is a dict with `columns` and optional `unique`.

```python
store.write(
    "users",
    data_frame=data,
    with_indices={
        "unique_user_id_index": {"columns": ["user_id"], "unique": True},
        "user_name_index": {"columns": ["user_id", "username"]},
    },
)
```

Notes:

- Indexes are created with `checkfirst=True`, so re-running is safe.
- If `write_option="replace"`, the table is dropped and you'll need to pass
  `with_indices` again to recreate them.

## Upserts (`ON CONFLICT DO UPDATE`)

When appending to a table with a unique index, you can upsert by passing
`on_conflict_do_update`. Params are forwarded to SQLAlchemy's
[`on_conflict_do_update`](https://github.com/sqlalchemy/sqlalchemy/blob/main/lib/sqlalchemy/dialects/postgresql/dml.py#L107-L149).

```python
store.write(
    "users",
    data_frame=data1,
    write_option="append",
    with_indices={
        "unique_user_id_index": {"columns": ["user_id"], "unique": True},
    },
)

store.write(
    "users",
    data_frame=data2,
    write_option="append",
    on_conflict_do_update={
        "index_elements": ["user_id"],
        "set_": {
            "username": "EXCLUDED.username",
            "country": "EXCLUDED.country",
        },
    },
)
```

Values in `set_` are passed through SQLAlchemy's `text()` — use them to
reference the incoming row via `EXCLUDED.<column>`, or to apply SQL expressions.

## Automatic column migration

On `append`, if the `DataFrame` contains columns not present in the destination
table, they are added via `ALTER TABLE ... ADD COLUMN` before the insert. Types
are inferred from the `DataFrame` dtype using pandas' own SQL type mapping.

```python
store.write("users", data_frame=data_with_3_cols, write_option="replace")
store.write("users", data_frame=data_with_4_cols, write_option="append")
# the 4th column is added automatically; existing rows get NULL for it
```

Only column *additions* are supported. Type changes and drops are not.

## Table name validation

Table names must match `^[a-z0-9_]+$` — lowercase letters, digits, and
underscores. Anything else raises `ValueError`.

```python
FeatureStore.validate_table_name("users")       # ok
FeatureStore.validate_table_name("users-2024")  # ValueError
```

## Testing with pytest

`sql-feature-store` ships its own pytest plugin, so downstream users can
integration-test against a real PostgreSQL database without rewriting the
fixtures themselves. Install the `testing` extra:

```bash
pip install sql-feature-store[testing]
```

The extra pulls in [`pytest-postgresql`](https://pypi.org/project/pytest-postgresql/),
and the plugin auto-registers three fixtures via pytest's `pytest11` entry
point:

| Fixture | Scope | Purpose |
|---|---|---|
| `sql_feature_store_postgres_proc` | session | Backing Postgres process. Spawned for you by default, or delegated to an external server (see below). |
| `sql_feature_store_config` | function | `PostgresConfig` pointed at the test database, with a **fresh random `write_schema` per test** (dropped `CASCADE` on teardown). |
| `sql_feature_store_fixture` | function | A ready `FeatureStore` built from the config above. Engine is disposed on teardown. |

Schemas are namespaced `sfs_test_<random>` and dropped after each test, so
runs stay isolated even if a test bails out part-way.

### Example

```python
import pandas as pd

def test_write_and_read(sql_feature_store_fixture, sql_feature_store_config):
    store = sql_feature_store_fixture
    schema = sql_feature_store_config.write_schema

    data = pd.DataFrame({"user_id": [1, 2, 3]})
    store.write("users", data_frame=data, write_option="replace")

    result = store.read(f"SELECT * FROM {schema}.users")
    assert result.equals(data)
```

### Spawn-per-session vs external database

By default the plugin spawns a throwaway `postgres` process for the test
session. That requires the `postgres` binary on `PATH` — handy for local dev,
not always available in CI.

If `SFS_POSTGRES_HOST` is set, the plugin skips spawning and connects to the
provided database instead. Intended for CI jobs that already run a Postgres
service container.

| Variable | Required in external mode | Default |
|---|---|---|
| `SFS_POSTGRES_HOST` | yes (presence toggles the mode) | — |
| `SFS_POSTGRES_USER` | yes | — |
| `SFS_POSTGRES_PASSWORD` | yes | — |
| `SFS_POSTGRES_PORT` | no | `5432` |
| `SFS_POSTGRES_DB` | no | `postgres` |

The connecting role needs `CREATE` privilege on the database — per-test
schemas are created by `FeatureStore` on the fly
(see [Schema creation](#schema-creation)).

### Importing the fixtures explicitly

If you prefer to re-export the fixtures from your own `conftest.py` rather
than relying on plugin auto-discovery:

```python
from sql_feature_store.testing import (
    sql_feature_store_config,
    sql_feature_store_fixture,
    sql_feature_store_postgres_proc,
)
```

See `tests/integration/` in the source tree for the full set of usage patterns
(indexes, upserts, column migration, chunked reads, etc.).
