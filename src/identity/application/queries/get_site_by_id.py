"""Load one site."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import SiteDTO


@dataclass(frozen=True)
class GetSiteByIdQuery(Query):

    site_id: str

    Result = SiteDTO | None
