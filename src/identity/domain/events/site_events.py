from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime

from ..value_objects.ids import DirectoryId, SiteId
from ..value_objects.location import Location
from ..value_objects.site_kind import SiteKind


class SiteCreated(BaseEvent[SiteId]):
    """A site was created."""

    def __init__(
        self,
        site_id: SiteId,
        *,
        directory_id: DirectoryId,
        name: str,
        location: Location,
        kind: SiteKind,
        address: str | None,
    ) -> None:
        super().__init__()
        self.site_id = site_id
        self.directory_id = directory_id
        self.name = name
        self.location = location
        self.kind = kind
        self.address = address

    def get_aggregate_id(self) -> SiteId:
        return self.site_id

    def get_event_name(self) -> str:
        return "users.site.created"

    def to_payload(self) -> dict:
        return {
            "site_id": self.site_id.value,
            "directory_id": self.directory_id.value,
            "name": self.name,
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
            "kind": self.kind.value,
            "address": self.address,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "SiteCreated":
        return cls(
            SiteId(payload["site_id"]),
            directory_id=DirectoryId(payload["directory_id"]),
            name=payload["name"],
            location=Location(payload["latitude"], payload["longitude"]),
            kind=SiteKind(payload["kind"]),
            address=payload["address"],
        )


class SiteActivated(BaseEvent[SiteId]):
    """A site was (re)activated."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self.site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self.site_id

    def get_event_name(self) -> str:
        return "users.site.activated"

    def to_payload(self) -> dict:
        return {"site_id": self.site_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "SiteActivated":
        return cls(SiteId(payload["site_id"]))


class SiteDeactivated(BaseEvent[SiteId]):
    """A site was deactivated."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self.site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self.site_id

    def get_event_name(self) -> str:
        return "users.site.deactivated"

    def to_payload(self) -> dict:
        return {"site_id": self.site_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "SiteDeactivated":
        return cls(SiteId(payload["site_id"]))


class SiteMadePrincipal(BaseEvent[SiteId]):
    """A site became the principal site of its directory."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self.site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self.site_id

    def get_event_name(self) -> str:
        return "users.site.made_principal"

    def to_payload(self) -> dict:
        return {"site_id": self.site_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "SiteMadePrincipal":
        return cls(SiteId(payload["site_id"]))


class SiteMadeAnnex(BaseEvent[SiteId]):
    """The previous principal site of a directory became an annex."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self.site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self.site_id

    def get_event_name(self) -> str:
        return "users.site.made_annex"

    def to_payload(self) -> dict:
        return {"site_id": self.site_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "SiteMadeAnnex":
        return cls(SiteId(payload["site_id"]))


class SiteImported(BaseEvent[SiteId]):
    """A site taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        site_id: SiteId,
        *,
        directory_id: DirectoryId,
        name: str,
        location: Location,
        kind: SiteKind,
        address: str | None,
        active: bool,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.site_id = site_id
        self.directory_id = directory_id
        self.name = name
        self.location = location
        self.kind = kind
        self.address = address
        self.active = active
        self.created_at = created_at

    def get_aggregate_id(self) -> SiteId:
        return self.site_id

    def get_event_name(self) -> str:
        return "users.site.imported"

    def to_payload(self) -> dict:
        return {
            "site_id": self.site_id.value,
            "directory_id": self.directory_id.value,
            "name": self.name,
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
            "kind": self.kind.value,
            "address": self.address,
            "active": self.active,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "SiteImported":
        return cls(
            SiteId(payload["site_id"]),
            directory_id=DirectoryId(payload["directory_id"]),
            name=payload["name"],
            location=Location(payload["latitude"], payload["longitude"]),
            kind=SiteKind(payload["kind"]),
            address=payload["address"],
            active=payload["active"],
            created_at=decode_datetime(payload["created_at"]),
        )
