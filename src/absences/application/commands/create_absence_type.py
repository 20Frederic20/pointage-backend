from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class CreateAbsenceTypeCommand(Command):
    """Create a new absence type."""

    name: str
    paid: bool
    counts_as_work_time: bool
    deducts_balance: bool
