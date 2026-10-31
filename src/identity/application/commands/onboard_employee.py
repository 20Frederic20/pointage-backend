"""Onboard a new person: their account, the employee and the first assignment."""

from dataclasses import dataclass
from datetime import date

from core.application import Command
from identity.domain import Role


@dataclass(frozen=True)
class OnboardEmployeeCommand(Command):
    """Create the employee (and its account, unless the email already has one) in one transaction.

    ``role`` applies to the employee record, and to the account when it is new;
    ``EMPLOYEE`` when omitted. Without ``password`` a new account logs in with an
    emailed code. An existing account is reused untouched (names and password ignored).
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
    # Who acts (from the access token): responsible roles only, capped by rank.
    actor_user_id: str = ""
    actor_role: str = ""
