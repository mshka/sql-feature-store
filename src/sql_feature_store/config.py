from dataclasses import dataclass


@dataclass(frozen=True)
class PostgresConfig:
    """Connection parameters for a PostgreSQL instance.

    The caller is responsible for sourcing these values (env vars, AWS Secrets
    Manager, Vault, static config, etc.). This library does not fetch or rotate
    credentials on its own.
    """

    host: str
    user: str
    password: str
    dbname: str
    port: int = 5432
    write_schema: str = "predictions"
