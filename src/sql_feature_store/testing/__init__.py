"""Pytest fixtures for testing code that depends on ``sql-feature-store``.

Install the ``testing`` extra and pytest will auto-discover the plugin via the
``pytest11`` entry point registered in ``pyproject.toml``::

    pip install sql-feature-store[testing]

The fixtures listed here are re-exported for consumers that prefer to import
them explicitly (e.g. to re-export from their own ``conftest.py``).
"""

from sql_feature_store.testing.plugin import (
    sql_feature_store_config,
    sql_feature_store_fixture,
    sql_feature_store_postgres_proc,
)

__all__ = [
    "sql_feature_store_config",
    "sql_feature_store_fixture",
    "sql_feature_store_postgres_proc",
]
