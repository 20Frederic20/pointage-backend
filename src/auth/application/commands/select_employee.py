from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class SelectEmployeeCommand(Command):
    """Several active companies: open the session on the chosen employee record."""

    selection_token: str
    employee_id: str
