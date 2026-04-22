"""Tests for index creation via ``with_indices``."""

import pandas as pd


class TestIndices:
    @staticmethod
    def test_unique_index_is_created(
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

        store.write(
            "users",
            data_frame=data,
            with_indices={
                "unique_user_id_index": {"columns": ["user_id"], "unique": True}
            },
        )

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert result.equals(data)

        with store._engine.connect() as conn:
            indices = store._engine.dialect.get_indexes(
                conn, "users", schema=sql_feature_store_config.write_schema
            )
        assert len(indices) == 1
        assert indices[0]["name"] == "unique_user_id_index"
        assert indices[0]["unique"] is True
        assert indices[0]["column_names"] == ["user_id"]
