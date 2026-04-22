# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-22

Initial public release on PyPI.

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
- `PostgresConfig` dataclass for connection parameters. Fields include
  `write_schema` (default `"predictions"`) and `create_schema_if_missing`
  (default `True`) — `FeatureStore` runs `CREATE SCHEMA IF NOT EXISTS` on
  its first `write()` call and memoises the check for the lifetime of the
  instance. Set to `False` to require that the schema exists up front
  (raises `sqlalchemy.exc.ProgrammingError` otherwise).
- Table-name validation against `^[a-z0-9_]+$`.
- Pytest plugin shipped with the package via the `pytest11` entry point.
  Install with `pip install sql-feature-store[testing]` to get three
  auto-discovered fixtures:
  - `sql_feature_store_postgres_proc` — session-scoped Postgres process
    (spawned locally, or connected to an external server when
    `SFS_POSTGRES_HOST` is set).
  - `sql_feature_store_config` — `PostgresConfig` with a fresh random
    `write_schema` per test (dropped `CASCADE` on teardown).
  - `sql_feature_store_fixture` — a ready `FeatureStore` for the per-test
    schema.
- `sql_feature_store.testing` subpackage re-exporting the fixtures for
  explicit import from a consumer's `conftest.py`.
- Documentation: [`docs/usage.md`](docs/usage.md) API reference and
  [`docs/roadmap.md`](docs/roadmap.md) forward plan.
- Development tooling: `pre-commit` (black, flake8, isort, pygrep-hooks),
  `pytest` + `pytest-postgresql`, `tox` for one-command local verification,
  GitHub Actions CI with Codecov coverage reporting, and a tag-driven
  release workflow (`.github/workflows/release.yml`) publishing to PyPI
  via Trusted Publishing.

[Unreleased]: https://github.com/mshka/sql-feature-store/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/mshka/sql-feature-store/releases/tag/v0.2.0
