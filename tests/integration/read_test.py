"""Tests for ``FeatureStore.read`` — single-DataFrame and chunked iterator."""

import pandas as pd


class TestRead:
    @staticmethod
    def test_read_returns_all_rows(sql_feature_store_fixture, sql_feature_store_config):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1] * 10_001,
                "username": ["alice"] * 10_001,
                "country": ["US"] * 10_001,
            }
        )
        store.write("users", data_frame=data, write_option="replace")

        result = store.read(
            f"select * from {sql_feature_store_config.write_schema}.users"
        )
        assert len(result) == 10_001

    @staticmethod
    def test_read_streams_chunks(sql_feature_store_fixture, sql_feature_store_config):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1] * 10,
                "username": ["alice"] * 10,
                "country": ["US"] * 10,
            }
        )
        store.write("users", data_frame=data, write_option="replace")

        batches = 0
        for chunk in store.read(
            f"select * from {sql_feature_store_config.write_schema}.users",
            chunksize=2,
        ):
            batches += 1
            assert len(chunk) == 2
        assert batches == 5
