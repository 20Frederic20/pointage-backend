"""Login support: resolve an email to credentials (or nothing)."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import UserCredentialsDTO


@dataclass(frozen=True)
class GetUserByEmailQuery(Query):
    """The credentials record for ``email``, or ``None``.

    Only the auth context's login handler consumes the result — it carries
    the password hash and never crosses the HTTP boundary.
    """

    email: str

    Result = UserCredentialsDTO | None