"""Which employee record a login opens: one per company, never an inactive one."""

from dataclasses import dataclass

from ...domain.errors import NoActiveEmploymentError
from ..dtos import AccountCredentialsDTO, EmploymentDTO


@dataclass(frozen=True)
class BoundSession:
    employee_id: str | None
    role: str


@dataclass(frozen=True)
class SelectionRequired:
    employments: tuple[EmploymentDTO, ...]


def resolve_employment(
    account: AccountCredentialsDTO, employments: list[EmploymentDTO]
) -> BoundSession | SelectionRequired | None:
    """``None``: the employee number named an inactive record (a refused login).

    * by employee number: that record;
    * by email: no record at all → the account's role; one active → it;
      several active → the client chooses; none active → ``NoActiveEmploymentError``.
    """
    active = [e for e in employments if e.is_active]
    if account.employee_id is not None:
        chosen = next((e for e in active if e.employee_id == account.employee_id), None)
        return BoundSession(chosen.employee_id, chosen.role) if chosen else None
    if not employments:
        return BoundSession(None, account.role)
    if not active:
        raise NoActiveEmploymentError("No active employee record for this account", context=account.id)
    if len(active) == 1:
        return BoundSession(active[0].employee_id, active[0].role)
    return SelectionRequired(tuple(active))
