"""Onboard a new person: their account, the employee and the first assignment."""

from dataclasses import dataclass
from datetime import date

from core.application import Command
from identity.domain import Role


@dataclass(frozen=True)
class OnboardEmployeeCommand(Command):
    """Create the account and the employee in one transaction.

    ``role`` applies to both; ``EMPLOYEE`` when omitted. Without
    ``password`` the account logs in with an emailed code.
    """

    email: str
    directory_id: str
    employee_number: str
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: Role | None = None
    phone: str | None = None
    is_active: bool | None = None
    # First day of the initial assignment; today when omitted.
    assignment_start_date: date | None = None
    # Site of the initial assignment; the directory's principal site when omitted.
    site_id: str | None = None
