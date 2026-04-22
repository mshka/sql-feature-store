"""Tests for the automatic-schema-creation path of :meth:`FeatureStore.write`.

Each test starts with a randomly-named schema that doesn't yet exist (provided
by :func:`sql_feature_store.testing.plugin.sql_feature_store_config`), so the
"first write should CREATE SCHEMA" path is exercised naturally.
"""

import dataclasses

import pandas as pd
import pytest
from sqlalchemy import event
from sqlalchemy.exc import ProgrammingError

from sql_feature_store.store import FeatureStore


class TestAutoCreateSchema:
    @staticmethod
    def test_write_auto_creates_schema_when_enabled(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        schema = sql_feature_store_config.write_schema

        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
            }
        )
        store.write("users", data_frame=data)

        with store._engine.connect() as conn:
            assert store._engine.dialect.has_schema(conn, schema)

        result = store.read(f"select * from {schema}.users")
        assert result.equals(data)

    @staticmethod
    def test_write_issues_create_schema_only_once_across_writes(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture

        executed: list[str] = []

        @event.listens_for(store._engine, "before_cursor_execute")
        def capture(conn, cursor, statement, parameters, context, executemany):
            executed.append(statement)

        data = pd.DataFrame({"user_id": [1, 2, 3]})
        store.write("users", data_frame=data)
        store.write("users", data_frame=data, write_option="append")
        store.write("users", data_frame=data, write_option="append")

        create_schema_stmts = [s for s in executed if "CREATE SCHEMA" in s.upper()]
        assert len(create_schema_stmts) == 1

    @staticmethod
    def test_write_fails_when_schema_missing_and_autocreate_disabled(
        sql_feature_store_config,
    ):
        config = dataclasses.replace(
            sql_feature_store_config, create_schema_if_missing=False
        )
        store = FeatureStore(config=config)
        try:
            with pytest.raises(ProgrammingError):
                store.write(
                    "users",
                    data_frame=pd.DataFrame({"user_id": [1, 2, 3]}),
                )
        finally:
            store._engine.dispose()
