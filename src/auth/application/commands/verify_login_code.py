from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class VerifyLoginCodeCommand(Command):
    """Exchange identifier (email or employee number) + emailed code for a token pair."""

    identifier: str
    code: str
