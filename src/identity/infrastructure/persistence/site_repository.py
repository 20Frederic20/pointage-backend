"""SQLAlchemy adapter for the Site aggregate."""

from datetime import UTC, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import Site
from ...domain.repositories import ISiteRepository
from ...domain.value_objects.ids import SiteId
from .models import SiteModel


class SiteRepository(ISiteRepository):
    """Same versioned save protocol as :class:`UserRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, site_id: SiteId) -> Site:
        row = await self._session.get(SiteModel, site_id.value)
        if row is None:
            raise NotFoundError(f"Site {site_id.value} not found", context=site_id.value)
        return self._to_aggregate(row)

    async def exists(self, site_id: SiteId) -> bool:
        row = await self._session.scalar(select(SiteModel.id).where(SiteModel.id == site_id.value))
        return row is not None

    async def save(self, site: Site) -> None:
        if site.version == 0:
            await self._insert(site)
        else:
            await self._update(site)
        site._advance_version()

    async def delete(self, site_id: SiteId) -> None:
        await self._session.execute(delete(SiteModel).where(SiteModel.id == site_id.value))

    async def _insert(self, site: Site) -> None:
        try:
            await self._session.execute(
                insert(SiteModel).values(
                    id=site.id.value,
                    name=site.name,
                    address=site.address,
                    active=site.active,
                    created_at=site.created_at or datetime.now(UTC),
                    updated_at=site.updated_at or datetime.now(UTC),
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(f"Site {site.id} already exists", context=site.id.value) from exc

    async def _update(self, site: Site) -> None:
        result = await self._session.execute(
            update(SiteModel.__table__)
            .where(SiteModel.id == site.id.value)
            .where(SiteModel.version_id == site.version)
            .values(
                name=site.name,
                address=site.address,
                active=site.active,
                updated_at=site.updated_at or datetime.now(UTC),
                version_id=site.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Site {site.id} was modified concurrently (stale version {site.version})",
                context=site.id.value,
            )

    def _to_aggregate(self, row) -> Site:
        return Site(
            SiteId(row.id),
            name=row.name,
            address=row.address,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
