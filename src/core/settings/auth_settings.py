from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Auth settings — JWT issuance and refresh-token lifetimes.

    ``jwt_secret`` is required with no default: the app must fail fast at
    startup rather than silently sign tokens with some placeholder. In
    production it comes from the environment / AWS Secrets Manager (PRD
    §9.2); locally, put a generated value in ``.env`` (see ``.env.example``).
    """

    jwt_secret: str
    jwt_issuer: str = "pointage"
    jwt_algorithm: str = "HS256"
    # PRD §9.1 — access tokens live 15 minutes, refresh tokens 7 days.
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
