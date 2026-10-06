from pydantic_settings import BaseSettings, SettingsConfigDict


class MailSettings(BaseSettings):
    """Outgoing mail (SMTP).

    Defaults target the Mailpit container of ``docker-compose.yml`` from the
    host: it accepts anything and shows the messages at http://localhost:8045.
    Production sets ``SMTP_HOST`` / ``SMTP_PORT`` / ``SMTP_USERNAME`` /
    ``SMTP_PASSWORD`` / ``SMTP_STARTTLS`` / ``MAIL_FROM`` in the environment.
    """

    smtp_host: str = "localhost"
    smtp_port: int = 1045
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    mail_from: str = "Pointage <no-reply@pointage.local>"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
