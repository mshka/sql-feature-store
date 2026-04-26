"""Integration tests for ``FeatureStore.get_online_features_sql``.

The unit-test temptation here ("just assert the rendered string equals X") is
a trap — it pins SQLAlchemy's string output, not our SQL semantics. Instead
the strong test is "execute the rendered SQL against the real Postgres and
assert the rows match", which is what ``test_rendered_sql_round_trips...``
does. The looser string assertions cover the schema-override path, where
the renderer's correctness *is* the contract (the SQL never runs against a
schema we control in CI for that case).
"""

import pandas as pd
from sqlalchemy import text

from sql_feature_store import FeatureView


class TestGetOnlineFeaturesSql:
    @staticmethod
    def test_rendered_sql_mentions_table_entity_and_features(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        view = FeatureView(
            table="users",
            entity="user_id",
            features=["country", "age"],
        )

        rendered = store.get_online_features_sql(entity_ids=[1, 2, 3], view=view)

        assert rendered  # non-empty
        assert "users" in rendered
        assert "user_id" in rendered
        assert "country" in rendered
        assert "age" in rendered
        assert sql_feature_store_config.write_schema in rendered

    @staticmethod
    def test_rendered_sql_round_trips_via_engine(
        sql_feature_store_fixture, sql_feature_store_config
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame(
            {
                "user_id": [1, 2, 3, 4],
                "country": ["US", "US", "FR", "DE"],
                "age": [21, 34, 47, 19],
            }
        )
        store.write("users", data_frame=data, write_option="replace")

        view = FeatureView(table="users", entity="user_id", features=["country", "age"])
        rendered = store.get_online_features_sql(entity_ids=[1, 3], view=view)

        # Execute the rendered string directly — strongest possible test that
        # `_sql` returns something `get_online_features` could actually run.
        with store._engine.connect() as conn:  # noqa: SLF001
            rows = conn.execute(text(rendered)).fetchall()

        result = pd.DataFrame(rows, columns=["user_id", "country", "age"]).sort_values(
            "user_id", ignore_index=True
        )
        expected = data.iloc[[0, 2]].reset_index(drop=True)
        assert result.equals(expected)

    @staticmethod
    def test_read_schema_override_appears_in_rendered_sql(
        sql_feature_store_fixture,
    ):
        store = sql_feature_store_fixture
        view = FeatureView(table="users", entity="user_id", features=["country"])

        rendered = store.get_online_features_sql(
            entity_ids=[1], view=view, read_schema="some_other_schema"
        )

        # Loose substring assertion is appropriate here: we're testing *our*
        # propagation of the kwarg into the static `table(..., schema=...)`,
        # not SQLAlchemy's quoting rules.
        assert "some_other_schema" in rendered
        assert "users" in rendered
