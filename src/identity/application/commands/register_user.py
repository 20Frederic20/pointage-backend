"""Account creation: the founding ADMIN, then accounts created by an ADMIN."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RegisterUserCommand(Command):
    """Create a user account.

    Public only while no account exists (the founding ADMIN). Afterwards
    ``requested_by_role`` must be ``ADMIN``; it is filled by the router from
    the caller's access token, never from the request body.

    Without ``password`` the account logs in with an emailed code.
    """

    email: str
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    directory_name: str | None = None
    role: str | None = None
    requested_by_role: str | None = None
