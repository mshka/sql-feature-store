# Roadmap

Forward-looking plan for `sql-feature-store`. Living document — priorities
shift, but the guiding principles below are load-bearing and shouldn't.

## Version plan at a glance

| Phase | Scope                       | Target version |
|-------|-----------------------------|----------------|
| 0     | First public PyPI release   | `0.2.0`        |
| 1     | Online feature store        | `0.3.x` – `0.8.x` |
| 2     | Multi-dialect (MySQL first) | `0.9.x`        |
| 3     | Offline capabilities        | `1.0.0` →      |

1.0.0 is cut after Phase 2 is complete and the online + multi-dialect
API surface has stabilised.

## Guiding principles

- **Stay small.** The library should do one thing well: read and write
  features against a SQL database from pandas. If a feature can live in
  user code or a downstream tool, it doesn't belong here.
- **Testability is first-class.** The shipped pytest plugin
  (`sql-feature-store[testing]`, random-schema-per-test) is a feature, not
  a convenience. Every new capability must be testable against a real
  database with zero setup.
- **Explicit beats magical.** Users declare schemas, views, types, and
  indices. The library doesn't guess.
- **Backwards compatibility while pre-1.0 is best-effort, not a promise.**
  Breaking changes are fine but must be flagged in `CHANGELOG.md` and the
  release notes.

## Phase 0 — Public pre-1.0 release

**Target version: `0.2.0`.**

Goal: get on PyPI so people can `pip install sql-feature-store`.

- [x] Add a release workflow (`.github/workflows/release.yml`): build on
      tag, publish to PyPI via trusted publishing or `PYPI_API_TOKEN`.
- [x] Sanity-check the built wheel: `release.yml` installs the built wheel
      with the `[testing]` extra into a clean venv and runs a pytest that
      uses the shipped fixture, proving the `pytest11` entry point survives
      packaging before PyPI upload.
- [x] README: install instructions (`pip install sql-feature-store`),
      PyPI + CI + coverage + Python-version badges.

Nothing else blocks the first release. If anything below wants to slip in
before 0.2.0, it needs a real reason; default is "ship now, iterate".

## Phase 1 — Online feature store

**Target versions: `0.3.x` through `0.8.x`. Still pre-1.0.**

Goal: turn the library from "a pandas-friendly Postgres upserter" into a
credible online feature store. Each sub-section is an independently
shippable 0.x release; the exact version bump per sub-section is decided
at release time.

Two read paths coexist and stay explicit — neither wraps the other:

- `FeatureStore.read(sql_query, chunksize=None)` — the existing escape
  hatch for ad-hoc SQL. Returns a DataFrame. Unchanged by Phase 1.
- `FeatureStore.get_online_features(entity_ids, views, ...)` — typed,
  entity-keyed, view-driven. Added in this phase.

Callers pick per use-case; neither is deprecated. The point of
`FeatureView` is to make the *second* path work; the first path stays
SQL-first and view-unaware.

### 1.1 — Feature views

- [x] `FeatureView` dataclass in `src/sql_feature_store/views.py`. Frozen,
      four fields:
  - `table: str` — source table name.
  - `entity: str` — entity-key column (what the online read looks up by).
  - `features: list[str]` — column names to expose.
  - `last_updated: str | None` — optional freshness column (default
    `None`).
- [x] No `Feature` dataclass. Per-feature metadata (dtype, nullable,
      description) lives in the SQL schema; callers who want typed
      returns pass a `dtype=` kwarg to `get_online_features`, same shape
      as `pd.read_sql`'s `dtype` argument.
- [x] Declarative only — no engine, no SQL, no registry. Users construct
      `FeatureView` instances in their own code and pass them to the
      store.

### 1.2 — Entity-keyed reads (single view)

- [ ] `FeatureStore.get_online_features(entity_ids, views, dtype=None,
      on_missing="null")` supporting one view per call.
- [ ] Deterministic return shape: one row per requested entity id,
      DataFrame indexed by the entity column, columns named
      `{view.table}.{feature}`.
- [ ] `on_missing="null" | "raise"`, default `"null"`.
- [ ] Optional `dtype` kwarg (same shape as `pd.read_sql`'s `dtype`) — if
      supplied, enforced on the returned DataFrame. No implicit typing.
- [ ] `FeatureStore.ensure_entity_index(view)` — one-line helper to add a
      unique index on the view's entity column if missing.

### 1.3 — Entity-keyed reads (multiple views)

- [ ] Multi-view merge on the entity column.
- [ ] Query-per-view is fine initially; revisit if profiling shows a
      single-query CTE would help.

### 1.4 — Freshness

- [ ] `FeatureStore.last_updated(view) -> datetime | None` — returns
      `SELECT MAX(view.last_updated) FROM view.table`. `None` when the
      view didn't declare a `last_updated` column.
- [ ] Document the `last_updated` write-side convention; do **not** start
      auto-writing it — keep producers in control.

### 1.5 — Serving ergonomics

- [ ] Document recommended pool settings for serving workloads.
- [ ] Optional: `FeatureStore.for_serving(...)` constructor with opinionated
      defaults (pool size, pre-ping, timeouts).
- [ ] Lazy-validation on first read: confirm the source table exposes the
      declared entity and feature columns, raise a clear error if not.

### 1.6 — Async read path

- [ ] `AsyncFeatureStore` over SQLAlchemy async engine + `asyncpg`.
- [ ] Parity with the sync read path; no async writes until a real user
      asks.

### 1.7 — Observability

- [ ] OpenTelemetry spans on `read` / `get_online_features` / `write`
      (optional dep — `[otel]` extra).
- [ ] Opt-in structured logger for per-call timings. No default logging —
      silence is golden.

Exit criterion for Phase 1: you can build a production inference service
on `FeatureStore` alone, with declared feature views, typed reads, async
support, and freshness monitoring.

## Phase 2 — Multi-dialect (MySQL first)

**Target version: `0.9.x`. Final pre-1.0 line.**

Goal: support MySQL with the same API surface. No dialect-specific leakage
in user code. Landing this is the last thing before 1.0 — after Phase 2
the library is considered API-stable and 1.0.0 is cut.

- [ ] Extract a `Dialect` abstraction covering the Postgres-specific bits:
      `CREATE SCHEMA IF NOT EXISTS`, `ON CONFLICT DO UPDATE`, identifier
      quoting, type mapping.
- [ ] Implement `PostgresDialect` (renaming, no behaviour change) and
      `MysqlDialect` (uses `INSERT ... ON DUPLICATE KEY UPDATE`,
      database-as-schema convention).
- [ ] Rename `PostgresConfig` → `DatabaseConfig`? TBD — could alias for
      compatibility.
- [ ] CI matrix gains a MySQL service; pytest plugin grows a
      `SFS_DB_BACKEND` env var to pick the backend in external-DB mode.
- [ ] Document supported dialects and their quirks.

Possible future dialects: SQLite (local dev), DuckDB (offline bridge).
Not committed, but worth keeping the abstraction honest.

## Phase 3 — Offline capabilities

**Target version: `1.0.0` and beyond.**

Goal: support training-data generation without pulling in a second tool.
Scope stays small — no backfill orchestration, no transformation DSL.
Offline work starts at 1.0.0; once an offline API exists, anything that
changes it post-1.0 follows semver properly (breaking change → 2.0).

- [ ] Grow `FeatureView` with optional `event_timestamp` and `created_at`
      column-name fields (4 → 6 fields, online path ignores them).
- [ ] `FeatureStore.get_historical_features(entity_df, views)` — point-in-time
      join over a DataFrame of `(entity_id, label_timestamp, ...)` rows.
- [ ] Document the "train on offline, serve on online" workflow.
- [ ] Revisit: if users want a separate Postgres/DuckDB backend for the
      offline store, we add a second config; we don't federate.

## Non-goals

Things that are **permanently out of scope** for this library. If they
become needed, they go in a sibling project, not here.

- Feature lineage / dependency graphs.
- Transformation DSL / computed features.
- Web UI or standalone service.
- Multi-store federation (two backends fronted by one API).
- Access control / per-feature permissions.
- Drift / data-quality monitoring.
- Caching layer (users compose their own on top).
- Streaming ingest / CDC integration.

Most of these are legitimate feature-store concerns. They just aren't
*this* library's job.
