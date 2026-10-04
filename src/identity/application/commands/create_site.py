from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class CreateSiteCommand(Command):
    """Create a site."""

    name: str
    address: str | None = None
