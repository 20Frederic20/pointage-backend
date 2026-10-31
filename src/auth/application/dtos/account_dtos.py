"""What auth needs to know about an identity account — nothing more.

The password hash is the only sensitive field; it stays in the application
layer and never crosses the HTTP boundary.
"""

from dataclasses import dataclass

from core.application import DTO


@dataclass(frozen=True)
class AccountCredentialsDTO(DTO):
    """``password_hash`` is ``None`` for an account that logs in by code.

    ``email`` is where login codes go, whatever identifier the caller typed.
    """

    id: str
    email: str
    role: str
    is_active: bool
    password_hash: str | None
    # Set when the identifier was an employee number: that record, and no other.
    employee_id: str | None = None


@dataclass(frozen=True)
class AccountDTO(DTO):
    id: str
    role: str
    is_active: bool


@dataclass(frozen=True)
class EmploymentDTO(DTO):
    """One employee record of an account: the company it works for and its role there."""

    employee_id: str
    company_name: str | None
    role: str
    is_active: bool
