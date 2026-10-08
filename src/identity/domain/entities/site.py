"""The Site aggregate — a physical place of one directory, where employees punch."""

from datetime import datetime
from typing import Self

from core.domain.entity import AggregateRoot

from ..errors.errors import PrincipalSiteCannotBeDeactivatedError
from ..events.site_events import SiteActivated, SiteCreated, SiteDeactivated, SiteMadePrincipal
from ..value_objects.ids import DirectoryId, SiteId
from ..value_objects.location import Location
from ..value_objects.site_kind import SiteKind


class Site(AggregateRoot[SiteId]):
    """A site belongs to exactly one directory and carries the GPS position
    employees are checked against when they punch.

    Each directory has one ``PRINCIPAL`` site; the others are ``ANNEX`` sites.
    The "one principal per directory" rule spans several sites, so the
    handlers enforce it (``CreateSiteHandler``, ``MakeSitePrincipalHandler``),
    backed by a partial unique index in the database.
    """

    __slots__ = ("_active", "_address", "_directory_id", "_kind", "_location", "_name")

    def __init__(
        self,
        site_id: SiteId,
        *,
        directory_id: DirectoryId,
        name: str,
        location: Location,
        kind: SiteKind = SiteKind.ANNEX,
        address: str | None = None,
        active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(site_id, created_at=created_at, updated_at=updated_at, version=version)
        self._directory_id = directory_id
        self._name = name.strip()
        self._location = location
        self._kind = SiteKind(kind)
        self._address = address
        self._active = active

    @classmethod
    def create(
        cls,
        site_id: SiteId,
        *,
        directory_id: DirectoryId,
        name: str,
        location: Location,
        kind: SiteKind,
        address: str | None = None,
    ) -> Self:
        """Factory for a brand-new site; records :class:`SiteCreated`."""
        site = cls(
            site_id,
            directory_id=directory_id,
            name=name,
            location=location,
            kind=kind,
            address=address,
        )
        site.record_event(SiteCreated(site_id))
        return site

    def is_principal(self) -> bool:
        return self._kind is SiteKind.PRINCIPAL

    def make_principal(self) -> None:
        """No-op when already principal. The caller demotes the previous one."""
        if self.is_principal():
            return
        if not self._active:
            raise PrincipalSiteCannotBeDeactivatedError(
                f"Site {self._name!r} is inactive and cannot become principal",
                context=self.id.value,
            )
        self._kind = SiteKind.PRINCIPAL
        self.touch()
        self.record_event(SiteMadePrincipal(self.id))

    def make_annex(self) -> None:
        """Demotion, only as the other half of :meth:`make_principal` on another site."""
        if not self.is_principal():
            return
        self._kind = SiteKind.ANNEX
        self.touch()

    def activate(self) -> None:
        """``activer``: no-op when already active."""
        if self._active:
            return
        self._active = True
        self.touch()
        self.record_event(SiteActivated(self.id))

    def deactivate(self) -> None:
        """``desactiver``: no-op when already inactive. A principal site cannot
        be deactivated: its directory would be left without a principal."""
        if not self._active:
            return
        if self.is_principal():
            raise PrincipalSiteCannotBeDeactivatedError(
                f"Site {self._name!r} is the principal site: make another site principal first",
                context=self.id.value,
            )
        self._active = False
        self.touch()
        self.record_event(SiteDeactivated(self.id))

    @property
    def directory_id(self) -> DirectoryId:
        return self._directory_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def location(self) -> Location:
        return self._location

    @property
    def kind(self) -> SiteKind:
        return self._kind

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def active(self) -> bool:
        return self._active
