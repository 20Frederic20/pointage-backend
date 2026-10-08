from enum import StrEnum


class SiteKind(StrEnum):
    """A directory has exactly one principal site; every other site is an annex."""

    PRINCIPAL = "PRINCIPAL"
    ANNEX = "ANNEX"
