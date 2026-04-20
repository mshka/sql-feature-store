import os

import pytest
from sql_feature_store.config import PostgresConfig

os.environ["ENV"] = "TEST"

# flake8: noqa: E402
from tests.postgres_db_utils import (
    _postgres_config_from_request,
    _postgres_db_session,
    create_postgres_test_db,
)

test_db = create_postgres_test_db()


@pytest.fixture
def postgres_config(request) -> PostgresConfig:
    return _postgres_config_from_request(request)


@pytest.fixture
def patched_store(postgres_config: PostgresConfig):
    def _db_session():
        return _postgres_db_session(postgres_config)

    return _db_session
