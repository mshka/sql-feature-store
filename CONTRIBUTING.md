# Contributing

Thanks for your interest in contributing to `sql-feature-store`.

## Requirements

- Python `>=3.10,<3.13`
- PostgreSQL (required by `pytest-postgresql`, which spawns a real `postgres`
  process for the integration tests)
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

## Setup

```bash
git clone git@github.com:mshka/sql-feature-store.git
cd sql-feature-store
poetry install            # runtime + dev deps
pre-commit install        # set up the git hook (run once per clone)
```

Python-level dependencies are declared in `pyproject.toml` and locked in
`poetry.lock`.

## Running tests

```bash
poetry run pytest
```

With coverage (matches CI):

```bash
poetry run pytest \
  --cov=sql_feature_store \
  --cov-report=term-missing \
  --cov-fail-under=90
```

`pytest-postgresql` spawns a real `postgres` process for the test session, so
the `postgres` binary must be on your `PATH`.

## Linting and formatting

Pre-commit runs `black`, `flake8`, `isort`, and a few `pygrep-hooks` on commit.
You can run the full suite manually:

```bash
poetry run pre-commit run --all-files
```

## Opening a pull request

1. Fork and branch off `main` (e.g. `fix/something`, `docs/something`).
2. Keep commits focused — one concern per commit, capitalized imperative
   subject (e.g. "Add CONTRIBUTING guide", "Fix typo in write()").
3. Make sure `pytest` and `pre-commit run --all-files` pass locally.
4. Open a PR against `main`. CI must be green before merge.

Breaking changes are fine pre-`0.1.0`; call them out clearly in the PR
description and add an entry to `CHANGELOG.md` under `Unreleased`.
