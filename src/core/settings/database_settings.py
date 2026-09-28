from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database + Redis connection settings.

    ``database_url`` (env ``DATABASE_URL``) is an optional full SQLAlchemy URL
    that overrides the ``db_*`` fields — used for tests and non-Postgres
    drivers.
    """

    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int

    # Redis
    redis_host: str
    redis_port: int
    redis_db: int

    database_url: str | None = None

    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
