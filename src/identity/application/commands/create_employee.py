"""Create an employee and their first assignment to a directory."""

from dataclasses import dataclass
from datetime import date

from core.application import Command
from identity.domain import Role


@dataclass(frozen=True)
class CreateEmployeeCommand(Command):

    user_id: str
    directory_id: str
    employee_number: str
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
