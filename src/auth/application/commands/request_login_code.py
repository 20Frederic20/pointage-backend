from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RequestLoginCodeCommand(Command):
    """Email a one-time login code to a password-less account.

    ``identifier`` is an email or an employee number; the code always goes to
    the account's email.
    """

    identifier: str
