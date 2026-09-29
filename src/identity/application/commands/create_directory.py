"""Renaming the workspace."""

from dataclasses import dataclass

from core.application import Command
from identity.domain.value_objects.location import Location


@dataclass(frozen=True)
class CreateDirectoryCommand(Command):
    name: str
    code: str
    location: Location
