"""List the sites of a directory."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import SiteDTO


@dataclass(frozen=True)
class GetDirectorySitesQuery(Query):
    """Principal first, then the annexes."""

    directory_id: str

    Result = list[SiteDTO]
