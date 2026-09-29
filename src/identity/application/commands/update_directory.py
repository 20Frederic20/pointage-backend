"""Renaming the workspace."""

from dataclasses import dataclass

from core.application import Command
from identity.domain.value_objects.location import Location


@dataclass(frozen=True)
class UpdateDirectoryCommand(Command):
    name: str | None = None
    code: str | None = None
    location: Location | None = None
