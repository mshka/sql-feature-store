import contextlib
import dataclasses

import pandas as pd
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError

from sql_feature_store.store import FeatureStore


@contextlib.contextmanager
def _ephemeral_schema(engine, name):
    """Drop `name` before and after the block, so each test starts and ends
    against a clean slate even if an earlier run bailed out mid-test."""

    def drop():
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {name} CASCADE"))

    drop()
    try:
        yield
    finally:
        drop()


class TestAutoCreateSchema:
    @staticmethod
    def test_write_auto_creates_schema_when_enabled(postgres_config):
        cfg = dataclasses.replace(postgres_config, write_schema="auto_created_schema")
        store = FeatureStore(config=cfg)

        with _ephemeral_schema(store._engine, "auto_created_schema"):
            data = pd.DataFrame(
                {
                    "user_id": [1, 2, 3],
                    "username": ["alice", "bob", "carol"],
                }
            )
            store.write("users", data_frame=data)

            with store._engine.connect() as conn:
                assert store._engine.dialect.has_schema(conn, "auto_created_schema")

            data_written = store.read("select * from auto_created_schema.users")
            assert data_written.equals(data)

    @staticmethod
    def test_write_issues_create_schema_only_once_across_writes(postgres_config):
        cfg = dataclasses.replace(postgres_config, write_schema="memoized_schema")
        store = FeatureStore(config=cfg)

        executed: list[str] = []

        @event.listens_for(store._engine, "before_cursor_execute")
        def capture(conn, cursor, statement, parameters, context, executemany):
            executed.append(statement)

        with _ephemeral_schema(store._engine, "memoized_schema"):
            data = pd.DataFrame({"user_id": [1, 2, 3]})
            store.write("users", data_frame=data)
            store.write("users", data_frame=data, write_option="append")
            store.write("users", data_frame=data, write_option="append")

        create_schema_stmts = [s for s in executed if "CREATE SCHEMA" in s.upper()]
        assert len(create_schema_stmts) == 1

    @staticmethod
    def test_write_fails_when_schema_missing_and_autocreate_disabled(postgres_config):
        cfg = dataclasses.replace(
            postgres_config,
            write_schema="autocreate_disabled_schema",
            create_schema_if_missing=False,
        )
        store = FeatureStore(config=cfg)

        with _ephemeral_schema(store._engine, "autocreate_disabled_schema"):
            with pytest.raises(ProgrammingError):
                store.write(
                    "users",
                    data_frame=pd.DataFrame({"user_id": [1, 2, 3]}),
                )
