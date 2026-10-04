"""Create a directory under a site, optionally inside a parent directory."""

from dataclasses import dataclass

from core.application import Command
from identity.domain.value_objects.location import Location


@dataclass(frozen=True)
class CreateDirectoryCommand(Command):
    name: str
    code: str
    location: Location
    site_id: str
    parent_directory_id: str | None = None
