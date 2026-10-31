from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class CreateManagerTimeEntryCommand(Command):
    """A responsible punches for an employee: counted at once, stamped with the
    server time. The client sends neither the time nor the direction."""

    actor_user_id: str
    actor_role: str
    employee_id: str
    idempotency_key: str
