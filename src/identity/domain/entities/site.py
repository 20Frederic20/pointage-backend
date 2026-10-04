"""The Site aggregate — a physical place that directories belong to."""

from datetime import datetime
from typing import Self

from core.domain.entity import AggregateRoot

from ..events.site_events import SiteActivated, SiteCreated, SiteDeactivated
from ..value_objects.ids import SiteId


class Site(AggregateRoot[SiteId]):

    __slots__ = ("_active", "_address", "_name")

    def __init__(
        self,
        site_id: SiteId,
        *,
        name: str,
        address: str | None = None,
        active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(site_id, created_at=created_at, updated_at=updated_at, version=version)
        self._name = name.strip()
        self._address = address
        self._active = active

    @classmethod
    def create(cls, site_id: SiteId, *, name: str, address: str | None = None) -> Self:
        """Factory for a brand-new site; records :class:`SiteCreated`."""
        site = cls(site_id, name=name, address=address)
        site.record_event(SiteCreated(site_id))
        return site

    def activate(self) -> None:
        """``activer``: no-op when already active."""
        if self._active:
            return
        self._active = True
        self.touch()
        self.record_event(SiteActivated(self.id))

    def deactivate(self) -> None:
        """``desactiver``: no-op when already inactive."""
        if not self._active:
            return
        self._active = False
        self.touch()
        self.record_event(SiteDeactivated(self.id))

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def active(self) -> bool:
        return self._active
