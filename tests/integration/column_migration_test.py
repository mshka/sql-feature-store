"""Tests for automatic ``ALTER TABLE ... ADD COLUMN`` on ``append``."""

import pandas as pd


class TestColumnMigration:
    @staticmethod
    def test_new_column_added_on_append_without_index(
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
                "score": [1, 0],
            }
        )
        expected = pd.DataFrame(
            {
                "user_id": [1, 2, 3, 1, 2],
                "username": ["alice", "bob", "carol", "dave", "eve"],
                "country": ["US", "US", None, "DE", "US"],
                "score": [None, None, None, 1, 0],
            }
        )

        store.write("users", data_frame=data1, write_option="replace")
        store.write("users", data_frame=data2, write_option="append")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(expected)

    @staticmethod
    def test_new_column_added_on_append_with_index_and_upsert(
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
                "SCORE": [1, 0],
            }
        )
        expected = pd.DataFrame(
            {
                "user_id": [3, 1, 2],
                "username": ["carol", "dave", "eve"],
                "country": [None, "DE", "US"],
                "SCORE": [None, 1, 0],
            }
        )

        store.write(
            "users",
            data_frame=data1,
            write_option="replace",
            with_indices={
                "unique_user_id_index": {"columns": ["user_id"], "unique": True}
            },
        )
        store.write(
            "users",
            data_frame=data2,
            write_option="append",
            on_conflict_do_update={
                "index_elements": ["user_id"],
                "set_": {
                    "username": "EXCLUDED.username",
                    "country": "Excluded.country",
                    "SCORE": 'Excluded."SCORE"',
                },
            },
        )

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(expected)
