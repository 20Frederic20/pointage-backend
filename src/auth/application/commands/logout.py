from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class LogoutCommand(Command):
    """Revoke the session (the whole token family) behind a refresh token."""

    refresh_token: str
