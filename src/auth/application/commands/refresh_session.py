from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RefreshSessionCommand(Command):
    """Exchange a refresh token for a new token pair (rotation)."""

    refresh_token: str
