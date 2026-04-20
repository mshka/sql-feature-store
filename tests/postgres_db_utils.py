import os
from typing import Callable, List

import pandas as pd
from pytest_postgresql import factories
from sqlalchemy import Engine, schema

from sql_feature_store.config import PostgresConfig
from sql_feature_store.store import FeatureStore


class FakePostgresConnection:
    def __init__(self, engine) -> None:
        self.engine = engine

    def write_pandas_to_db(
        self, schema: str, table_name: str, df: pd.DataFrame
    ) -> None:
        df.to_sql(
            table_name, self.engine, schema=schema, if_exists="replace", index=False
        )


class PostgresDbSession:
    """Create DB session that make sure the DB exists and clean DB after use"""

    def __init__(self, engine: Engine, schemas: List[str] = []):
        self._engine = engine
        self._schemas = schemas
        self._fake_conn = FakePostgresConnection(self._engine)

    def __enter__(self):
        with self._engine.connect() as conn:
            for schema_name in self._schemas:
                if not self._engine.dialect.has_schema(conn, schema_name):
                    conn.execute(schema.CreateSchema(schema_name))
            conn.commit()
            conn.close()
        return self._fake_conn

    def __exit__(self, _exc_type, _exc_value, _traceback):
        with self._engine.connect() as conn:
            for schema_name in self._schemas:
                conn.execute(
                    schema.DropSchema(schema_name, cascade=True, if_exists=True)
                )
            conn.commit()
            conn.close()

        self._engine.dispose()


def create_postgres_test_db() -> Callable:
    return factories.postgresql_proc(
        host=os.environ.get("POSTGRES_HOST"),
        port=os.environ.get("POSTGRES_PORT"),
        dbname=os.environ.get("POSTGRES_DB", "postgres"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
    )


def _postgres_config_from_request(request) -> PostgresConfig:
    """Build a PostgresConfig pointing at the pytest-postgresql proc, or at
    the CI-provided Postgres when running under GitLab CI."""
    if os.environ.get("GITLAB_CI"):
        return PostgresConfig(
            host=str(os.environ["POSTGRES_HOST"]),
            port=int(os.environ["POSTGRES_PORT"]),
            user=str(os.environ["POSTGRES_USER"]),
            password=str(os.environ["POSTGRES_PASSWORD"]),
            dbname=str(os.environ.get("POSTGRES_DB", "postgres")),
        )

    _test_db = request.getfixturevalue("test_db")
    return PostgresConfig(
        host=str(_test_db.host),
        port=int(_test_db.port),
        user=str(_test_db.user),
        password=str(_test_db.password),
        dbname=str(_test_db.dbname),
    )


def _postgres_db_session(config: PostgresConfig) -> PostgresDbSession:
    fake_engine = FeatureStore(config=config)._engine
    return PostgresDbSession(fake_engine, [config.write_schema])
