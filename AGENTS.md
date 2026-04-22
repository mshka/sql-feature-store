# AGENTS.md

Instructions for AI coding assistants (Cursor, Claude Code, Codex, Aider, etc.)
working on this repo. Human contributors: see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

`sql-feature-store` is a pre-1.0 library. The public API may still change,
but every change must be deliberate — callers already depend on it.

## Commands

Assume Poetry 2.x and a Python in range `>=3.10,<3.14` are installed. The
`postgres` binary must be on `PATH` for the test suite (`pytest-postgresql`
spawns a real server).

```bash
poetry install --all-extras          # runtime + dev deps + [testing] extra
poetry run pytest                    # full test suite
poetry run pytest --cov=sql_feature_store --cov-fail-under=90
poetry run pre-commit run --all-files   # black, flake8, isort, pygrep-hooks
poetry run mypy src                  # type check (config in tox.ini)
```

The test suite lives under `tests/integration/` — every test currently hits a
real PostgreSQL database via the project's own pytest plugin
(`src/sql_feature_store/testing/plugin.py`, registered in `pyproject.toml`
under `[project.entry-points.pytest11]`). Any future unit tests go under a
sibling `tests/unit/`.

All of the above must pass before a change is considered done. CI runs the
same checks on Python 3.10 / 3.11 / 3.12 / 3.13.

## Conventions

### Respect the linter and type checker

- Do **not** suppress lint or type errors to make a change "pass". Fix the
  underlying issue. `warn_unused_ignores = True` is set, so stale
  `# type: ignore` comments will fail CI.
- If a `# type: ignore[...]` is truly unavoidable (third-party stub gap),
  narrow it to the specific error code and leave a one-line comment
  explaining why.
- `black` formatting (88-col line length) and `isort` with `profile = black`
  are enforced via pre-commit. Don't hand-format.

### Match existing patterns

Before introducing a new pattern, look at how it is already done elsewhere in
`src/sql_feature_store/store.py` and follow suit. A few concrete ones:

- **Type hints everywhere.** Public methods and non-trivial helpers have
  full signatures. No implicit `Optional` — write `Optional[int] = None`,
  not `int = None`.
- **No mutable default arguments.** Use `None` and normalize inside the
  function body (see `with_indices`, `on_conflict_do_update`, `indices`).
- **NaN/NaT/`pd.NA` coercion.** When sending DataFrame rows to the driver
  for upsert, coerce missing values to `None` via
  `df.astype(object).where(df.notna(), None)`. Inserting raw `float('nan')`
  lands as the string `"NaN"` in TEXT columns.
- **Table-name validation.** Any user-supplied identifier goes through the
  `^[a-z0-9_]+$` regex (`validate_table_name`). Don't interpolate
  identifiers into SQL without validation.
- **SQLAlchemy Core, not the ORM.** Use `Table`, `Index`, `insert`, `text`
  as the rest of the module does.
- **Imports.** Standard-lib, third-party, local — each group
  alphabetized. `isort` enforces this; don't fight it.

### Scope of changes

- Keep diffs minimal and focused on the stated task. If you notice an
  unrelated issue, mention it — don't silently fix it in the same change.
- Don't bump dependency versions as a side-effect of another change; that
  is Dependabot's job.
- User-facing changes go in `CHANGELOG.md` under `## [Unreleased]`.
  Breaking changes are fine pre-1.0 but must be called out there and in
  the PR description.
