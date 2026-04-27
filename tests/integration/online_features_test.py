"""Integration tests for ``FeatureStore.get_online_features``.

Each test pins one slice of the contract — column renaming, index, order
preservation, ``on_missing`` behaviour, empty input — so a regression in
any one of them surfaces with a focused failure rather than a vague
"DataFrame doesn't match" diff.
"""

import math

import pandas as pd
import pytest

from sql_feature_store import FeatureView


def _seed_users(store) -> pd.DataFrame:
    """Write a 4-row users table and return the source DataFrame."""
    data = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4],
            "country": ["US", "US", "FR", "DE"],
            "age": [21, 34, 47, 19],
        }
    )
    store.write("users", data_frame=data, write_option="replace")
    return data


class TestGetOnlineFeatures:
    @staticmethod
    def test_renames_feature_columns_with_view_table_prefix(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        result = store.get_online_features(entity_ids=[1, 2], view=view)

        assert list(result.columns) == ["users.country", "users.age"]

    @staticmethod
    def test_indexed_by_entity_column(sql_feature_store_fixture):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country"])

        result = store.get_online_features(entity_ids=[1, 2], view=view)

        assert result.index.name == "user_id"
        assert list(result.index) == [1, 2]

    @staticmethod
    def test_preserves_caller_order_even_when_rows_are_returned_in_db_order(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country"])

        result = store.get_online_features(entity_ids=[3, 1, 4], view=view)

        assert list(result.index) == [3, 1, 4]
        assert list(result["users.country"]) == ["FR", "US", "DE"]

    @staticmethod
    def test_default_on_missing_null_fills_unknown_entities_with_nan(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        result = store.get_online_features(entity_ids=[1, 999], view=view)

        assert list(result.index) == [1, 999]
        assert result.loc[1, "users.country"] == "US"
        assert result.loc[999, "users.country"] is None or (
            isinstance(result.loc[999, "users.country"], float)
            and math.isnan(result.loc[999, "users.country"])
        )
        assert math.isnan(result.loc[999, "users.age"])

    @staticmethod
    def test_partial_match_returns_expected_dataframe_with_nulls_in_order(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        result = store.get_online_features(entity_ids=[2, 999, 3], view=view)

        expected = pd.DataFrame(
            {
                "users.country": ["US", float("nan"), "FR"],
                "users.age": [34.0, float("nan"), 47.0],
            },
            index=pd.Index([2, 999, 3], name="user_id"),
        )
        pd.testing.assert_frame_equal(result, expected)

    @staticmethod
    def test_on_missing_skip_drops_unknown_entities_and_preserves_order(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        result = store.get_online_features(
            entity_ids=[2, 999, 3], view=view, on_missing="skip"
        )

        expected = pd.DataFrame(
            {"users.country": ["US", "FR"], "users.age": [34, 47]},
            index=pd.Index([2, 3], name="user_id"),
        )
        pd.testing.assert_frame_equal(result, expected)

    @staticmethod
    def test_on_missing_raise_returns_normally_when_all_entities_exist(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        result = store.get_online_features(
            entity_ids=[1, 2], view=view, on_missing="raise"
        )

        expected = pd.DataFrame(
            {"users.country": ["US", "US"], "users.age": [21, 34]},
            index=pd.Index([1, 2], name="user_id"),
        )
        pd.testing.assert_frame_equal(result, expected)

    @staticmethod
    def test_on_missing_raise_lists_all_missing_entities(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country"])

        with pytest.raises(KeyError) as excinfo:
            store.get_online_features(
                entity_ids=[1, 999, 1000], view=view, on_missing="raise"
            )

        message = str(excinfo.value)
        assert "999" in message
        assert "1000" in message
        assert "users" in message

    @staticmethod
    def test_empty_entity_ids_returns_empty_dataframe_with_correct_shape(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        _seed_users(store)
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        result = store.get_online_features(entity_ids=[], view=view)

        assert len(result) == 0
        assert list(result.columns) == ["users.country", "users.age"]
        assert result.index.name == "user_id"
