from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings for SocialCRM."""

    app_name: str = "SocialCRM"
    app_version: str = "0.0.1"
    app_env: str
    app_port: int
    app_debug: bool = True

    # Logger
    log_level: str = "DEBUG"
    log_file: str = "logs/app.log"
    log_format: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    # CORS — explicit allowlist of allowed origins (JSON list, e.g.
    # ["http://localhost:5173"]). Credentials are enabled only when the list is
    # non-empty and contains no "*".
    cors_origins: list[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
