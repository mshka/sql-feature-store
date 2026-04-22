"""Pytest plugin shipping fixtures for integration-testing against a real
PostgreSQL database.

Two modes of operation:

1. **Spawn-per-session (default).** If the ``SFS_POSTGRES_HOST`` environment
   variable is *not* set, a throwaway ``postgres`` process is spawned for the
   test session via ``pytest-postgresql``. Requires the ``postgres`` binary on
   ``PATH``.

2. **Use-external (opt-in via env).** If ``SFS_POSTGRES_HOST`` *is* set, no
   process is spawned — the fixtures connect to the provided database. This is
   the intended path for CI jobs that already run a Postgres service
   container. Recognised variables:

   - ``SFS_POSTGRES_HOST`` (required to switch modes)
   - ``SFS_POSTGRES_PORT`` (default ``5432``)
   - ``SFS_POSTGRES_USER`` (required in this mode)
   - ``SFS_POSTGRES_PASSWORD`` (required in this mode)
   - ``SFS_POSTGRES_DB`` (default ``postgres``)

Both modes give each test a fresh, randomly-named ``write_schema`` that is
dropped on teardown, so tests are isolated without the caller having to
manage schemas by hand.
"""

from __future__ import annotations

import os
import secrets
from typing import Any, Iterator

import pytest
from pytest_postgresql import factories
from sqlalchemy import text

from sql_feature_store.config import PostgresConfig
from sql_feature_store.store import FeatureStore

_EXTERNAL_HOST_ENV = "SFS_POSTGRES_HOST"


def _external_postgres_requested() -> bool:
    return bool(os.environ.get(_EXTERNAL_HOST_ENV))


def _external_postgres_config(write_schema: str) -> PostgresConfig:
    missing = [
        name
        for name in ("SFS_POSTGRES_USER", "SFS_POSTGRES_PASSWORD")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(
            f"{_EXTERNAL_HOST_ENV} is set, so the sql-feature-store testing "
            f"fixtures expect these variables too: {', '.join(missing)}."
        )
    return PostgresConfig(
        host=os.environ[_EXTERNAL_HOST_ENV],
        port=int(os.environ.get("SFS_POSTGRES_PORT", "5432")),
        user=os.environ["SFS_POSTGRES_USER"],
        password=os.environ["SFS_POSTGRES_PASSWORD"],
        dbname=os.environ.get("SFS_POSTGRES_DB", "postgres"),
        write_schema=write_schema,
    )


if _external_postgres_requested():

    @pytest.fixture(scope="session")
    def sql_feature_store_postgres_proc() -> None:
        """Placeholder returned when ``SFS_POSTGRES_HOST`` is set.

        The fixture chain still resolves to a real ``PostgresConfig`` via
        :func:`sql_feature_store_config`; this fixture just exists so other
        fixtures can depend on it unconditionally.
        """
        return None

else:
    # `dbname="postgres"` targets the default system database that always
    # exists on a fresh Postgres server; we then create a per-test schema
    # inside it via `sql_feature_store_config`. The branch-dependent shapes of
    # this fixture confuse mypy; pytest handles the indirection at runtime.
    sql_feature_store_postgres_proc = factories.postgresql_proc(dbname="postgres")  # type: ignore[assignment] # noqa: E501


@pytest.fixture
def sql_feature_store_config(
    sql_feature_store_postgres_proc: Any,
    request: pytest.FixtureRequest,
) -> PostgresConfig:
    """A :class:`PostgresConfig` with a fresh random ``write_schema`` per test.

    The schema is dropped (``CASCADE``) on teardown, so each test runs
    against a clean slate regardless of how the previous test exited.
    """
    write_schema = f"sfs_test_{secrets.token_hex(4)}"

    if _external_postgres_requested():
        config = _external_postgres_config(write_schema)
    else:
        proc = sql_feature_store_postgres_proc
        config = PostgresConfig(
            host=str(proc.host),
            port=int(proc.port),
            user=str(proc.user),
            password=str(proc.password),
            dbname=str(proc.dbname),
            write_schema=write_schema,
        )

    def _drop_schema() -> None:
        store = FeatureStore(config=config)
        try:
            with store._engine.begin() as conn:
                conn.execute(
                    text(f"DROP SCHEMA IF EXISTS {config.write_schema} CASCADE")
                )
        finally:
            store._engine.dispose()

    request.addfinalizer(_drop_schema)
    return config


@pytest.fixture
def sql_feature_store_fixture(
    sql_feature_store_config: PostgresConfig,
) -> Iterator[FeatureStore]:
    """A ready-to-use :class:`FeatureStore` pointed at the per-test schema.

    The underlying engine is disposed on teardown; the per-test schema is
    dropped by :func:`sql_feature_store_config`.
    """
    store = FeatureStore(config=sql_feature_store_config)
    try:
        yield store
    finally:
        store._engine.dispose()
