import re
from typing import Any, Dict, Iterator, List, Literal, Optional, Set, Union, cast

import numpy as np
import pandas as pd
from pandas.io import sql
from sqlalchemy import (
    URL,
    ColumnClause,
    Connection,
    Engine,
    Index,
    MetaData,
    Table,
    TableClause,
    column,
    create_engine,
    table,
    text,
)
from sqlalchemy.dialects.postgresql import insert

from sql_feature_store.config import PostgresConfig

DEFAULT_POOL_SIZE = 20
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_RECYCLE_SECONDS = 1800


class FeatureStore:
    """
    Pandas-native feature store backed by a SQL database (PostgreSQL).

    Methods:
        - read(sql_query):
            read data with sql query and return dataframe
        - write(table_name, data_frame, write_option, etc..):
            write data to the schema configured on `PostgresConfig.write_schema`
    """

    def __init__(
        self,
        config: PostgresConfig,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
        pool_recycle: int = DEFAULT_POOL_RECYCLE_SECONDS,
    ) -> None:
        self._config = config
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_recycle = pool_recycle

        self._engine: Engine = self._get_postgresql_engine()

    def _get_postgresql_engine(self) -> Engine:
        url = URL.create(
            "postgresql+psycopg2",
            username=self._config.user,
            password=self._config.password,
            host=self._config.host,
            port=self._config.port,
            database=self._config.dbname,
        )
        return create_engine(
            url,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            pool_pre_ping=True,
            pool_recycle=self._pool_recycle,
            echo=False,
        )

    @staticmethod
    def _normalize_on_conflict_do_update(_query: Optional[Dict]) -> Optional[Dict]:
        if not _query:
            return _query

        if _query.get("set_"):
            _query["set_"] = {_k: text(_v) for _k, _v in _query["set_"].items()}

        return _query

    @staticmethod
    def _dtype_to_postgresql_type(
        conn: Connection, column_name: str, column_type: np.dtype
    ) -> str:
        # Reference: https://github.com/pandas-dev/pandas/blob/main/pandas/tests/io/test_sql.py#L1589-L1595  # noqa: E501
        """
        Method to return postgres type from dtype by re-using logic of pandas test.
        """
        _df = pd.DataFrame(columns=[column_name], dtype=column_type)
        _db = sql.SQLDatabase(conn)  # type: ignore
        _table = sql.SQLTable("tmp_for_type", _db, frame=_df)
        return str(_table.table.columns[column_name].type)

    def _table_exist(self, table_name: str, conn: Connection) -> bool:
        return self._engine.dialect.has_table(
            connection=conn,
            table_name=table_name,
            schema=self._config.write_schema,
        )

    def _get_table_columns(
        self, table_name: str, conn: Connection, schema: Optional[str] = None
    ) -> List:
        schema = schema or self._config.write_schema
        return self._engine.dialect.get_columns(
            connection=conn, table_name=table_name, schema=schema
        )

    def _new_columns_in_data(
        self,
        table_name: str,
        conn: Connection,
        data_columns: List[str],
        schema: Optional[str] = None,
    ) -> Set:
        schema = schema or self._config.write_schema
        _table_columns = self._get_table_columns(
            table_name=table_name, conn=conn, schema=schema
        )
        _table_column_names = set([tc["name"] for tc in _table_columns])
        _new_columns_in_data = set(data_columns) - _table_column_names
        return _new_columns_in_data

    def _add_columns_to_table(
        self,
        conn: Connection,
        table_name: str,
        column_name: str,
        column_type: np.dtype,
        schema: Optional[str] = None,
    ) -> None:
        schema = schema or self._config.write_schema
        _column_type = self._dtype_to_postgresql_type(conn, column_name, column_type)
        _table_name = ".".join([schema, table_name])
        _stmt = text(
            f'ALTER TABLE {_table_name} ADD COLUMN "{column_name}" {_column_type}'
        )

        conn.execute(_stmt)

    def _create_index_if_not_exists(
        self,
        table_name: str,
        index_name: str,
        columns: List[ColumnClause],
        unique: bool,
    ) -> None:
        _index = Index(
            index_name,
            *columns,
            unique=unique,
            _table=Table(table_name, MetaData(), schema=self._config.write_schema),
        )
        _index.create(self._engine, checkfirst=True)

    def _create_indices_if_not_exists(
        self, table_name: str, indices: Optional[Dict] = None
    ) -> None:
        if not indices:
            return

        for _name, _options in indices.items():
            self._create_index_if_not_exists(
                table_name=table_name,
                index_name=_name,
                columns=[column(_col_name) for _col_name in _options["columns"]],
                unique=_options.get("unique", False),
            )

    def _upsert_records(
        self,
        conn: Connection,
        table: TableClause,
        data_frame: pd.DataFrame,
        on_conflict_do_update: Optional[Dict] = None,
    ) -> int:
        if on_conflict_do_update:
            _normalized = self._normalize_on_conflict_do_update(on_conflict_do_update)
            assert _normalized is not None  # truthy input always yields a dict back
            _stmt = insert(table).on_conflict_do_update(**_normalized)
        else:
            _stmt = insert(table).on_conflict_do_nothing()

        # Replace NaN/NaT with None so the driver emits SQL NULL instead of
        # coercing to the string "NaN" (which can happen for object/text columns).
        # pandas-stubs rejects `other=None` on the `.where(...)` overload even
        # though it's a supported runtime idiom, so cast to satisfy mypy.
        _records = (
            data_frame.astype(object)
            .where(data_frame.notna(), cast(Any, None))
            .to_dict(orient="records")
        )
        # `to_dict` returns `list[dict[Hashable, Any]]`, but every column name
        # in a DataFrame backed by SQL is a string at runtime.
        return conn.execute(_stmt, cast(List[Dict[str, Any]], _records)).rowcount

    def _read_with_chunks(
        self, sql_query: str, chunksize: int
    ) -> Iterator[pd.DataFrame]:
        with self._engine.connect() as conn:
            cursor = conn.execution_options(stream_results=True).execute(
                text(sql_query)
            )
            while True:
                rows = cursor.fetchmany(chunksize)
                if not rows:
                    break
                yield pd.DataFrame(rows, columns=list(cursor.keys()))
            cursor.close()
            conn.close()

    def _read(self, sql_query: str) -> pd.DataFrame:
        with self._engine.connect() as conn:
            _output = pd.read_sql(text(sql_query), con=conn)
            conn.close()
            return _output

    def read(
        self, sql_query: str, chunksize: Optional[int] = None
    ) -> Union[Iterator[pd.DataFrame], pd.DataFrame]:
        """
        Read data and return as DataFrame.

        Parameters:
        sql_query (str): SQL query to return data.

        Returns:
        DataFrame: DataFrame of rows returned.
        """
        if chunksize:
            return self._read_with_chunks(sql_query, chunksize)
        else:
            return self._read(sql_query)

    @staticmethod
    def validate_table_name(table_name: str) -> None:
        if not re.match(r"^[a-z0-9_]+$", table_name):
            raise ValueError(
                (
                    f"Invalid table name '{table_name}': Table names should use "
                    "only lowercase letters, numbers, and underscores"
                )
            )

    def write(
        self,
        table_name: str,
        data_frame: pd.DataFrame,
        write_option: Literal["fail", "replace", "append"] = "replace",
        dtype_mapping: Optional[Dict[str, np.dtype]] = None,
        chunksize: int = 1000,
        with_indices: Optional[Dict[str, Dict[str, Union[List, bool]]]] = None,
        on_conflict_do_update: Optional[Dict[str, Union[Dict, List, str]]] = None,
    ) -> Optional[int]:
        """
        Write data frame to the schema configured on `PostgresConfig.write_schema`. # noqa: E501

        Parameters:
        table_name (str):
            Table name, destination of the data.
        data_frame (DataFrame):
            Pandas data frame with data to write to table.
        write_option (str, ["fail", "replace", "append"]):
            Action to take if the table already exists in the database, default to replace
                - append: Append to the table, might occure in duplicate rows if no index are created
                - replace: Replace table with new table containing current data from data frame
                - fail: Raise an error if table already exists
        dtype_mapping (Dict[str, np.dtype], Optional):
            Specifying the datatype for columns.
        chunksize (int, optional):
            Specify the number of rows in each batch to be written at a time, default is 1000
        with_indices: (Dict[str, Dict[str, List[str], bool]], optional):
            Pass info for indexes to be created.
            example: { "index_name": {"columns": [column1, column2], "unique": True}}
                This will create an index named index_name for column1 and column2 that is unique
                multiple indices can be passed in one option {index1_name: {}, index2_name: {}}
                if write method is replace you will need to create the index each time you write the data
        on_conflict_do_update: (Dict[str, Union[Dict, List]], optional):
            see https://github.com/sqlalchemy/sqlalchemy/blob/main/lib/sqlalchemy/dialects/postgresql/dml.py#L107-L149
            for details, params are passed through a dictionary example:
            { "index_elements": ["user_id"], "set_": {"username": "Excluded.username"}}
            this would tell the sql to update the username with new one if duplicate exist on user_id

        """
        self.validate_table_name(table_name=table_name)

        # create table if it doesn't exist
        _cols: List[ColumnClause] = [
            column(_col_name) for _col_name in data_frame.columns.tolist()
        ]
        _table = table(table_name, *_cols, schema=self._config.write_schema)

        with self._engine.begin() as conn:
            if (write_option in ["fail", "replace"]) or (
                not self._table_exist(table_name, conn)
            ):
                # Create table then create index
                _rowcount = data_frame.to_sql(
                    name=table_name,
                    con=conn,
                    if_exists=write_option,
                    index=False,
                    index_label=None,
                    schema=self._config.write_schema,
                    chunksize=chunksize,
                    dtype=dtype_mapping,  # type: ignore
                    method=None,
                )
                conn.commit()

                self._create_indices_if_not_exists(
                    table_name=table_name, indices=with_indices
                )
            elif write_option == "append":
                # Check if table need migration
                # Migration supported are only for new column
                if _new_columns_to_create := self._new_columns_in_data(
                    conn=conn,
                    table_name=table_name,
                    data_columns=data_frame.columns.tolist(),
                ):
                    for _new_column in _new_columns_to_create:
                        self._add_columns_to_table(
                            conn, table_name, _new_column, data_frame[_new_column].dtype
                        )
                # Make sure index exists in case of on_conflict_do_update
                self._create_indices_if_not_exists(
                    table_name=table_name, indices=with_indices
                )
                _rowcount = self._upsert_records(
                    conn=conn,
                    table=_table,
                    data_frame=data_frame,
                    on_conflict_do_update=on_conflict_do_update,
                )
                conn.commit()

            conn.close()

            return _rowcount
