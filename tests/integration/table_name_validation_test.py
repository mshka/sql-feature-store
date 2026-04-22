"""Parametrized tests for the ``^[a-z0-9_]+$`` table-name regex."""

import pandas as pd
import pytest


class TestTableNameValidation:
    _MSG = "names should use only lowercase letters, numbers, and underscores"

    @staticmethod
    @pytest.mark.parametrize(
        "table_name, expected_to_raise",
        [
            ("table-name", True),
            ("table_name-", True),
            ("table name", True),
            ("table", False),
            ("table_name", False),
        ],
    )
    def test_table_name_validation(
        sql_feature_store_fixture, table_name, expected_to_raise
    ):
        store = sql_feature_store_fixture
        data = pd.DataFrame({"user_id": [1, 2, 3]})

        if expected_to_raise:
            with pytest.raises(ValueError, match=TestTableNameValidation._MSG):
                store.write(table_name, data_frame=data)
        else:
            store.write(table_name, data_frame=data)
