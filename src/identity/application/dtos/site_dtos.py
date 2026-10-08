from dataclasses import dataclass
from datetime import datetime

from core.application import DTO
from identity.domain.value_objects.location import Location

from ...domain.entities import Site


@dataclass(frozen=True)
class SiteDTO(DTO):
    id: str
    directory_id: str
    name: str
    location: Location
    kind: str
    active: bool
    address: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(cls, site: Site) -> "SiteDTO":
        return cls(
            id=site.id.value,
            directory_id=site.directory_id.value,
            name=site.name,
            location=site.location,
            kind=site.kind.value,
            active=site.active,
            address=site.address,
            created_at=site.created_at,
            updated_at=site.updated_at,
        )
