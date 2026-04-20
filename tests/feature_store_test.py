import pandas as pd
import pytest

from sql_feature_store.store import (
    DEFAULT_MAX_OVERFLOW,
    DEFAULT_POOL_RECYCLE_SECONDS,
    DEFAULT_POOL_SIZE,
    FeatureStore,
)


class TestFeatureStoreOperations:
    @staticmethod
    def test_writing_to_db(patched_store, postgres_config):
        with patched_store() as fake_postgres_connection:
            store = FeatureStore(config=postgres_config)
            data = pd.DataFrame(
                {
                    "user_id": [1, 2, 3],
                    "username": ["alice", "bob", "carol"],
                    "country": ["US", "US", None],
                }
            )

            fake_postgres_connection.write_pandas_to_db(
                schema=postgres_config.write_schema, table_name="users", df=data
            )

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )

            assert data.equals(data_written)

    @staticmethod
    def test_creating_db_with_index(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
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
                with_indicies={
                    "unique_user_id_index": {"columns": ["user_id"], "unique": True}
                },
            )

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(data)
            with store._engine.connect() as conn:
                indicies = store._engine.dialect.get_indexes(
                    conn, "users", schema=postgres_config.write_schema
                )
                conn.close()
            assert len(indicies) == 1
            assert indicies[0]["name"] == "unique_user_id_index"
            assert indicies[0]["unique"] is True
            assert indicies[0]["column_names"] == ["user_id"]

    @staticmethod
    def test_appending_data(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
            data_to_write = pd.DataFrame(
                {
                    "user_id": [1, 2, 3],
                    "username": ["alice", "bob", "carol"],
                    "country": ["US", "US", None],
                }
            )
            expected = pd.DataFrame(
                {
                    "user_id": [1, 2, 3, 1, 2, 3],
                    "username": ["alice", "bob", "carol", "alice", "bob", "carol"],
                    "country": ["US", "US", None, "US", "US", None],
                }
            )

            store.write("users", data_frame=data_to_write, write_option="append")
            store.write("users", data_frame=data_to_write, write_option="append")

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(expected)

    @staticmethod
    def test_appending_data_with_unique_index(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
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
                with_indicies={
                    "unique_user_id_index": {"columns": ["user_id"], "unique": True}
                },
            )
            store.write("users", data_frame=data2, write_option="append")

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(data1)

    @staticmethod
    def test_appending_data_with_unique_and_on_conflict_statement(
        patched_store, postgres_config
    ):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
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
                with_indicies={
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

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(expected)

    @staticmethod
    def test_writing_data_with_replace_when_table_dont_exist(
        patched_store, postgres_config
    ):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
            data = pd.DataFrame(
                {
                    "user_id": [1, 2, 3],
                    "username": ["alice", "bob", "carol"],
                    "country": ["US", "US", None],
                }
            )

            store.write("users", data_frame=data, write_option="replace")

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(data)

    @staticmethod
    def test_replacing_data(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
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

            store.write("users", data_frame=data1, write_option="replace")
            store.write("users", data_frame=data2, write_option="replace")

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(data2)

    @staticmethod
    def test_adding_data_with_different_columns_without_index(
        patched_store, postgres_config
    ):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
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

            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(expected)

    @staticmethod
    def test_adding_data_with_different_columns_with_index(
        patched_store, postgres_config
    ):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
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
                with_indicies={
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
            data_written = store.read(
                f"select * from {postgres_config.write_schema}.users"
            )
            assert data_written.equals(expected)

    @staticmethod
    def test_reading_from_db_by_chunks(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
            data = pd.DataFrame(
                {
                    "user_id": [1] * 10,
                    "username": ["alice"] * 10,
                    "country": ["US"] * 10,
                }
            )
            store.write("users", data_frame=data, write_option="replace")
            batch = 0
            for chunk in store.read(
                f"select * from {postgres_config.write_schema}.users", chunksize=2
            ):
                batch += 1
                assert len(chunk) == 2
            assert batch == 5

    @staticmethod
    def test_reading_from_db(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
            data = pd.DataFrame(
                {
                    "user_id": [1] * 10_001,
                    "username": ["alice"] * 10_001,
                    "country": ["US"] * 10_001,
                }
            )
            store.write("users", data_frame=data, write_option="replace")
            input = store.read(f"select * from {postgres_config.write_schema}.users")

            assert len(input) == 10_001

    @staticmethod
    @pytest.mark.parametrize(
        "table_name, will_raise_error, error_message",
        [
            (
                "table-name",
                True,
                "names should use only lowercase letters, numbers, and underscores",
            ),
            (
                "table_name-",
                True,
                "names should use only lowercase letters, numbers, and underscores",
            ),
            (
                "table name",
                True,
                "names should use only lowercase letters, numbers, and underscores",
            ),
            ("table", False, ""),
            ("table_name", False, ""),
        ],
    )
    def test_table_name_validation(
        patched_store,
        postgres_config,
        table_name,
        will_raise_error,
        error_message,
    ):
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)
            if will_raise_error:
                with pytest.raises(ValueError, match=error_message):
                    store.write(
                        table_name,
                        data_frame=pd.DataFrame({"user_id": [1, 2, 3]}),
                    )
            else:
                store.write(
                    table_name,
                    data_frame=pd.DataFrame({"user_id": [1, 2, 3]}),
                )

    @staticmethod
    def test_engine_uses_pooling_with_pre_ping_and_recycle(
        patched_store, postgres_config
    ):
        # Stale/rotated connections are handled by SQLAlchemy's pool via
        # pool_pre_ping + pool_recycle. Verify the engine is configured
        # accordingly.
        with patched_store() as _:
            store = FeatureStore(config=postgres_config)

            pool = store._engine.pool
            assert pool.size() == DEFAULT_POOL_SIZE
            assert pool._max_overflow == DEFAULT_MAX_OVERFLOW
            assert pool._recycle == DEFAULT_POOL_RECYCLE_SECONDS
            assert store._engine.pool._pre_ping is True

    @staticmethod
    def test_engine_pool_config_is_overridable(patched_store, postgres_config):
        with patched_store() as _:
            store = FeatureStore(
                config=postgres_config,
                pool_size=3,
                max_overflow=1,
                pool_recycle=60,
            )

            pool = store._engine.pool
            assert pool.size() == 3
            assert pool._max_overflow == 1
            assert pool._recycle == 60
