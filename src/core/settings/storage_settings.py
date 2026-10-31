from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """S3-compatible object storage (MinIO) for selfies.

    Defaults target the MinIO container of ``docker-compose.yml`` from the
    host. Production sets ``S3_ENDPOINT`` / ``S3_ACCESS_KEY`` /
    ``S3_SECRET_KEY`` / ``S3_BUCKET`` / ``S3_SECURE`` in the environment.
    """

    s3_endpoint: str = "localhost:9010"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "punch-photos"
    s3_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
