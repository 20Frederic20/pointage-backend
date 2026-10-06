from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class LoginCommand(Command):
    """Exchange email + password for a token pair."""

    email: str
    password: str
