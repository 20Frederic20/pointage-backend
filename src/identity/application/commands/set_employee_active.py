from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class SetEmployeeActiveCommand(Command):
    """Deactivate (leave, departure) or reactivate an employee record."""

    actor_user_id: str
    actor_role: str
    employee_id: str
    active: bool
