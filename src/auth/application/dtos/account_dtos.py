"""What auth needs to know about an identity account — nothing more.

The password hash is the only sensitive field; it stays in the application
layer and never crosses the HTTP boundary.
"""

from dataclasses import dataclass

from core.application import DTO


@dataclass(frozen=True)
class AccountCredentialsDTO(DTO):
    """``password_hash`` is ``None`` for an account that logs in by code."""

    id: str
    role: str
    is_active: bool
    password_hash: str | None


@dataclass(frozen=True)
class AccountDTO(DTO):
    id: str
    role: str
    is_active: bool
