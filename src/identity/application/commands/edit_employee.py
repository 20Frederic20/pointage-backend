from dataclasses import dataclass

from core.application import Command
from identity.domain import Role


@dataclass(frozen=True)
class EditEmployeeCommand(Command):
    """Edit an employee record: names (account-wide), phone and role (per company).

    ``None`` leaves a field untouched.
    """

    actor_user_id: str
    actor_role: str
    employee_id: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role: Role | None = None
