from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Write database + read database + Redis connection settings.

    * Write database (``db_*`` / ``DATABASE_URL``): the event store, the
      unique keys, the outbox and auth's tables. Commands write here.
    * Read database (``read_db_*`` / ``READ_DATABASE_URL``): the read models,
      fed by the projection runner. Queries read here.

    A full SQLAlchemy URL (``DATABASE_URL`` / ``READ_DATABASE_URL``)
    overrides the matching ``*_db_*`` fields — used for tests and
    non-Postgres drivers.
    """

    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int

    read_db_name: str | None = None
    read_db_user: str | None = None
    read_db_password: str | None = None
    read_db_host: str | None = None
    read_db_port: int | None = None

    # Redis
    redis_host: str
    redis_port: int
    redis_db: int

    database_url: str | None = None
    read_database_url: str | None = None

    @model_validator(mode="after")
    def _require_read_database(self) -> Self:
        fields = (self.read_db_name, self.read_db_user, self.read_db_password, self.read_db_host, self.read_db_port)
        if self.read_database_url is None and any(value is None for value in fields):
            raise ValueError("Set READ_DATABASE_URL or all of READ_DB_NAME/USER/PASSWORD/HOST/PORT")
        return self

    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """The write database."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def SQLALCHEMY_READ_DATABASE_URI(self) -> str:
        """The read database."""
        if self.read_database_url:
            return self.read_database_url
        return (
            f"postgresql+psycopg://{self.read_db_user}:{self.read_db_password}"
            f"@{self.read_db_host}:{self.read_db_port}/{self.read_db_name}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
