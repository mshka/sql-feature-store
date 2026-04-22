"""Tests for the three ``write_option`` modes: ``replace``, ``append``, ``fail``.

The plain round-trip (write then read) also lives here so there's one obvious
place to look for "does a `.write()` show up in `.read()`?" style tests.
"""

import pandas as pd
import pytest


class TestWriteModes:
    @staticmethod
    def test_write_then_read_roundtrip(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
                "country": ["US", "US", None],
            }
        )

        store.write("users", data_frame=data, write_option="replace")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data)

    @staticmethod
    def test_replace_when_table_does_not_exist(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
                "country": ["US", "US", None],
            }
        )

        store.write("users", data_frame=data, write_option="replace")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data)

    @staticmethod
    def test_replace_overwrites_existing_rows(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data1 = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
                "country": ["US", "US", None],
            }
        )
        data2 = pd.DataFrame(
            {
                "user_id": [1, 2],
                "username": ["dave", "eve"],
                "country": ["DE", "US"],
            }
        )

        store.write("users", data_frame=data1, write_option="replace")
        store.write("users", data_frame=data2, write_option="replace")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data2)

    @staticmethod
    def test_append_accumulates_rows(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
                "country": ["US", "US", None],
            }
        )
        expected = pd.DataFrame(
            {
                "user_id": [1, 2, 3, 1, 2, 3],
                "username": ["alice", "bob", "carol", "alice", "bob", "carol"],
                "country": ["US", "US", None, "US", "US", None],
            }
        )

        store.write("users", data_frame=data, write_option="append")
        store.write("users", data_frame=data, write_option="append")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(expected)

    @staticmethod
    def test_fail_creates_table_when_missing(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
            }
        )

        store.write("users", data_frame=data, write_option="fail")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data)

    @staticmethod
    def test_fail_raises_when_table_exists(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "carol"],
            }
        )
        store.write("users", data_frame=data, write_option="replace")

        with pytest.raises(ValueError, match="already exists"):
            store.write("users", data_frame=data, write_option="fail")

        # The original data is still there untouched.
        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data)
