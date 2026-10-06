from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class VerifyLoginCodeCommand(Command):
    """Exchange email + emailed code for a token pair."""

    email: str
    code: str
