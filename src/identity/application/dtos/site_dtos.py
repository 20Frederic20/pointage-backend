from dataclasses import dataclass
from datetime import datetime

from core.application import DTO

from ...domain.entities import Site


@dataclass(frozen=True)
class SiteDTO(DTO):
    id: str
    name: str
    active: bool
    address: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(cls, site: Site) -> "SiteDTO":
        return cls(
            id=site.id.value,
            name=site.name,
            active=site.active,
            address=site.address,
            created_at=site.created_at,
            updated_at=site.updated_at,
        )
