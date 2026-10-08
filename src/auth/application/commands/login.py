from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class LoginCommand(Command):
    """Exchange identifier (email or employee number) + password for a token pair."""

    identifier: str
    password: str
