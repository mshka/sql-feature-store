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
