from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class CreateTimeProfileCommand(Command):
    """Create a new time profile."""

    name: str
    timezone: str
