from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class DeactivateSiteCommand(Command):
    """Deactivate a site."""

    site_id: str
