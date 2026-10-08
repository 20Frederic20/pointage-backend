from dataclasses import dataclass

from core.application import Command
from identity.domain.value_objects.location import Location


@dataclass(frozen=True)
class CreateSiteCommand(Command):
    """Create a site of a directory. The directory's first site becomes its
    principal site; the next ones are annexes."""

    directory_id: str
    name: str
    location: Location
    address: str | None = None
