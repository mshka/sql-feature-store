"""Unit tests for ``FeatureView``.

Pure-metadata dataclass — no DB, no I/O. We pin the contract surface that
downstream callers will rely on (frozen, field-based equality, default
``last_updated=None``) so accidental refactors of ``views.py`` show up as
test failures instead of silent behaviour changes.
"""

from dataclasses import FrozenInstanceError

import pytest

from sql_feature_store import FeatureView


class TestFeatureView:
    @staticmethod
    def test_constructs_with_required_fields_and_default_last_updated():
        view = FeatureView(table="users", entity="user_id", features=["country", "age"])

        assert view.table == "users"
        assert view.entity == "user_id"
        assert view.features == ["country", "age"]
        assert view.last_updated is None

    @staticmethod
    def test_constructs_with_explicit_last_updated():
        view = FeatureView(
            table="users",
            entity="user_id",
            features=["country"],
            last_updated="updated_at",
        )

        assert view.last_updated == "updated_at"

    @staticmethod
    def test_is_frozen():
        view = FeatureView(table="users", entity="user_id", features=["country"])

        with pytest.raises(FrozenInstanceError):
            view.table = "other"  # type: ignore[misc]

    @staticmethod
    def test_equality_is_field_based():
        a = FeatureView(table="users", entity="user_id", features=["country"])
        b = FeatureView(table="users", entity="user_id", features=["country"])
        c = FeatureView(table="users", entity="user_id", features=["age"])

        assert a == b
        assert a != c
