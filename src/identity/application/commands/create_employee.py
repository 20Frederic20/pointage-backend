"""Renaming the workspace."""

from dataclasses import dataclass

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
