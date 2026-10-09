"""Event-store adapter for the Site aggregate (write side)."""

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventStore

from ...domain.entities import Site
from ...domain.events import (
    SiteActivated,
    SiteCreated,
    SiteDeactivated,
    SiteImported,
    SiteMadeAnnex,
    SiteMadePrincipal,
)
from ...domain.repositories import ISiteRepository
from ...domain.value_objects import SiteKind
from ...domain.value_objects.ids import DirectoryId, SiteId

SITE_STREAM = "identity.site"

SITE_EVENT_TYPES = {
    "users.site.created": SiteCreated,
    "users.site.activated": SiteActivated,
    "users.site.deactivated": SiteDeactivated,
    "users.site.made_principal": SiteMadePrincipal,
    "users.site.made_annex": SiteMadeAnnex,
    "users.site.imported": SiteImported,
}

PRINCIPAL_KEY = "identity.site.principal"
"""Held by the principal site of each directory (key = directory id)."""


class EventSourcedSiteRepository(ISiteRepository):
    """A site is the replay of its stream. "One principal per directory" is a
    unique key the principal site holds, so two concurrent writers cannot
    both make a principal (same guarantee as the old partial unique index).
    """

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, site_id: SiteId) -> Site:
        events = await self._store.load(site_id.value, SITE_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Site {site_id.value} not found", context=site_id.value)
        return Site.rehydrate(site_id, events)

    async def exists(self, site_id: SiteId) -> bool:
        return await self._store.exists(site_id.value, SITE_STREAM)

    async def find_by_directory(self, directory_id: DirectoryId) -> list[Site]:
        ids = await self._store.find_stream_ids(SITE_STREAM, {"directory_id": directory_id.value})
        streams = await self._store.load_streams(ids, SITE_EVENT_TYPES)
        sites = [Site.rehydrate(SiteId(stream_id), events) for stream_id, events in streams.items()]
        return sorted(sites, key=lambda site: (not site.is_principal(), site.name))

    async def find_principal(self, directory_id: DirectoryId) -> Site | None:
        owner = await self._store.owner(PRINCIPAL_KEY, directory_id.value)
        return await self.get_by_id(SiteId(owner)) if owner is not None else None

    async def save(self, site: Site) -> None:
        events = site.domain_events
        for event in events:
            principal = (
                isinstance(event, SiteMadePrincipal)
                or (isinstance(event, SiteCreated | SiteImported) and event.kind is SiteKind.PRINCIPAL)
            )
            if principal:
                await self._store.reserve(PRINCIPAL_KEY, site.directory_id.value, site.id.value)
            elif isinstance(event, SiteMadeAnnex):
                await self._store.release(PRINCIPAL_KEY, site.directory_id.value, site.id.value)
        await self._store.append(
            stream_type=SITE_STREAM, stream_id=site.id.value, expected_version=site.version, events=events
        )
        site._advance_version(len(events))

    async def delete(self, site_id: SiteId) -> None:
        raise NotImplementedError("Event-sourced sites are never deleted")
