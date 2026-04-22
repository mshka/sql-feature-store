"""Tests for ``on_conflict_do_update`` upserts under ``append`` mode."""

import pandas as pd


class TestUpsert:
    @staticmethod
    def test_append_with_unique_index_rejects_duplicates(
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
                "user_id": [1, 2, 3],
                "username": ["dave", "eve", "frank"],
                "country": ["DE", "US", None],
            }
        )

        store.write(
            "users",
            data_frame=data1,
            write_option="append",
            with_indices={
                "unique_user_id_index": {"columns": ["user_id"], "unique": True}
            },
        )
        store.write("users", data_frame=data2, write_option="append")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data1)

    @staticmethod
    def test_append_with_on_conflict_do_update_updates_rows(
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
        expected = pd.DataFrame(
            {
                "user_id": [3, 1, 2],
                "username": ["carol", "dave", "eve"],
                "country": [None, "DE", "US"],
            }
        )

        store.write(
            "users",
            data_frame=data1,
            write_option="append",
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
                },
            },
        )

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(expected)
