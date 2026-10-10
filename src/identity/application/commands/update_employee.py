"""Update an employee and their first assignment to a directory."""

from dataclasses import dataclass

from core.application import Command
from identity.domain import Role


@dataclass(frozen=True)
class UpdateEmployeeCommand(Command):

    employee_id: str | None
    user_id: str | None
    directory_id: str | None
    employee_number: str | None
    role: Role | None
    phone: str | None
    is_active: bool | None
