"""Tests that the SQLAlchemy engine is built with pooling + pre-ping + recycle,
and that the knobs are overridable from :class:`FeatureStore`'s constructor."""

from sql_feature_store.store import (
    DEFAULT_MAX_OVERFLOW,
    DEFAULT_POOL_RECYCLE_SECONDS,
    DEFAULT_POOL_SIZE,
    FeatureStore,
)


class TestEnginePoolConfiguration:
    @staticmethod
    def test_defaults_use_pre_ping_and_recycle(sql_feature_store_config):
        store = FeatureStore(config=sql_feature_store_config)
        try:
            pool = store._engine.pool
            assert pool.size() == DEFAULT_POOL_SIZE
            assert pool._max_overflow == DEFAULT_MAX_OVERFLOW
            assert pool._recycle == DEFAULT_POOL_RECYCLE_SECONDS
            assert pool._pre_ping is True
        finally:
            store._engine.dispose()

    @staticmethod
    def test_pool_knobs_are_overridable(sql_feature_store_config):
        store = FeatureStore(
            config=sql_feature_store_config,
            pool_size=3,
            max_overflow=1,
            pool_recycle=60,
        )
        try:
            pool = store._engine.pool
            assert pool.size() == 3
            assert pool._max_overflow == 1
            assert pool._recycle == 60
        finally:
            store._engine.dispose()
