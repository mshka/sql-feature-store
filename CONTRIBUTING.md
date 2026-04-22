# Contributing

Thanks for your interest in contributing to `sql-feature-store`.

## Requirements

- Python `>=3.10,<3.14`
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
poetry install --all-extras   # runtime + dev deps + [testing] extra
pre-commit install            # set up the git hook (run once per clone)
```

Python-level dependencies are declared in `pyproject.toml` and locked in
`poetry.lock`.

## Running the full local gate

`tox` wires up the whole CI-equivalent pipeline (tests + coverage + lint +
mypy) in one command:

```bash
poetry run tox
```

This runs `coverage run -m pytest`, `coverage report` (fails under 90%),
`pre-commit run --all-files`, and `mypy src`.

### Running steps individually

```bash
poetry run pytest                              # tests only, no coverage
poetry run coverage run -m pytest              # tests with coverage
poetry run coverage report                     # 90% floor, matches CI
poetry run pre-commit run --all-files          # lint
poetry run mypy src                            # type check
```

`coverage run -m pytest` (rather than `pytest --cov=...`) is used so
coverage starts before pytest loads its entry-point plugins — we ship our
own `pytest11` plugin in `sql_feature_store.testing.plugin`, and
pytest-cov would undercount its package's import-time lines.

`pytest-postgresql` spawns a real `postgres` process for the test session,
so the `postgres` binary must be on your `PATH`.

## Opening a pull request

1. Fork and branch off `main` (e.g. `fix/something`, `docs/something`).
2. Keep commits focused — one concern per commit, capitalized imperative
   subject (e.g. "Add CONTRIBUTING guide", "Fix typo in write()").
3. Make sure `poetry run tox` passes locally.
4. Open a PR against `main`. CI must be green before merge.

Breaking changes are fine pre-`0.1.0`; call them out clearly in the PR
description and add an entry to `CHANGELOG.md` under `Unreleased`.
