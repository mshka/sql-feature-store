# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `PostgresConfig.create_schema_if_missing` (default `True`) — `FeatureStore`
  now runs `CREATE SCHEMA IF NOT EXISTS` on its first `write()` call and
  memoises the check for the lifetime of the instance. Set to `False` to
  require that the schema exists up front (raises
  `sqlalchemy.exc.ProgrammingError` otherwise).
- Pytest plugin shipped as part of the package (registered via the
  `pytest11` entry point). Install with `pip install sql-feature-store[testing]`
  to get three auto-discovered fixtures:
  - `sql_feature_store_postgres_proc` — session-scoped Postgres process
    (spawned locally, or connected to an external server when
    `SFS_POSTGRES_HOST` is set).
  - `sql_feature_store_config` — `PostgresConfig` with a fresh random
    `write_schema` per test (dropped `CASCADE` on teardown).
  - `sql_feature_store_fixture` — a ready `FeatureStore` for the per-test
    schema.
- New `sql_feature_store.testing` subpackage re-exporting the fixtures for
  explicit import from a consumer's `conftest.py`.

### Changed

- Integration tests moved under `tests/integration/` and split across per-
  feature files (`read_test.py`, `write_modes_test.py`, `indices_test.py`,
  `upsert_test.py`, `column_migration_test.py`,
  `table_name_validation_test.py`, `engine_pool_test.py`,
  `auto_create_schema_test.py`). No test behaviour changes.

### Removed

- Private test helpers `tests/postgres_db_utils.py`
  (`FakePostgresConnection`, `PostgresDbSession`) and the ad-hoc
  `patched_store` fixture — superseded by the shipped plugin, per-test
  random schemas, and auto-created `write_schema`.
- Redundant `test_writing_to_db` test that exercised only the now-deleted
  `FakePostgresConnection.write_pandas_to_db` helper; the same
  write-then-read round trip is covered by `TestWriteModes.
  test_write_then_read_roundtrip`.

## [0.1.0] - TBD

Initial public release.

### Added

- `FeatureStore` class with a pandas-native API over PostgreSQL:
  - `read(sql_query, chunksize=None)` — single-DataFrame or chunked iterator
    read using a server-side cursor.
  - `write(table_name, data_frame, write_option, ...)` — `fail` / `replace` /
    `append` modes.
  - Automatic table creation from a `DataFrame`.
  - Automatic column migration (`ALTER TABLE ... ADD COLUMN`) on `append`
    when the `DataFrame` has extra columns.
  - Index creation via `with_indices`.
  - `ON CONFLICT DO UPDATE` upserts via `on_conflict_do_update`.
  - Connection pooling with `pool_pre_ping` and configurable
    `pool_size` / `max_overflow` / `pool_recycle`.
- `PostgresConfig` dataclass for connection parameters (including
  `write_schema`, default `"predictions"`).
- Table-name validation against `^[a-z0-9_]+$`.
- Documentation in [`docs/usage.md`](docs/usage.md).
- Development tooling: `pre-commit` (black, flake8, isort, pygrep-hooks),
  `pytest` + `pytest-postgresql` + `pytest-cov`, GitHub Actions CI with
  Codecov coverage reporting.

[Unreleased]: https://github.com/mshka/sql-feature-store/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mshka/sql-feature-store/releases/tag/v0.1.0
