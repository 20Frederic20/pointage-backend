from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class ActivateSiteCommand(Command):
    """Activate a site."""

    site_id: str
