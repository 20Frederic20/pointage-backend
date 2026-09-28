"""Bootstrap signup: the founding user and their workspace, in one command."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RegisterUserCommand(Command):
    """Public registration — works only while no workspace exists yet."""

    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None
    directory_name: str | None = None
