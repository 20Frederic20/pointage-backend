from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class MakeSitePrincipalCommand(Command):
    """Make a site the principal site of its directory; the previous
    principal becomes an annex."""

    site_id: str
