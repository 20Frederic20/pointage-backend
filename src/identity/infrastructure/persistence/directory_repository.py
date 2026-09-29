"""SQLAlchemy adapter for the Directory aggregate."""

from datetime import UTC, datetime

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from identity.domain.value_objects.location import Location

from ...domain.entities import Directory
from ...domain.repositories import IDirectoryRepository
from ...domain.value_objects.ids import DirectoryId
from .models import DirectoryModel


class DirectoryRepository(IDirectoryRepository):
    """Same versioned save protocol as :class:`UserRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, directory_id: DirectoryId) -> Directory:
        row = await self._session.get(DirectoryModel, directory_id.value)
        if row is None:
            raise NotFoundError(
                f"Directory {directory_id} not found",
                context=directory_id.value,
            )
        return self._to_aggregate(row)

    async def exists(self, directory_id: DirectoryId) -> bool:
        row = await self._session.scalar(
            select(DirectoryModel.id).where(DirectoryModel.id == directory_id.value)
        )
        return row is not None

    async def exists_any(self) -> bool:
        row = await self._session.scalar(select(DirectoryModel.id).limit(1))
        return row is not None

    async def exists_by_code(self, value) -> bool:
        row = await self._session.scalar(
            select(DirectoryModel.id).where(DirectoryModel.code == value).limit(1)
        )
        return row is not None

    async def exists_by_code_or_name(self, value) -> bool:
        row = await self._session.scalar(
            select(DirectoryModel.id).where(
                or_(
                    DirectoryModel.code == value,
                    DirectoryModel.name == value
                )
            ).limit(1)
        )
        return row is not None

    async def save(self, directory: Directory) -> None:
        if directory.version == 0:
            await self._insert(directory)
        else:
            await self._update(directory)
        directory._advance_version()

    async def delete(self, directory_id: DirectoryId) -> None:
        await self._session.execute(
            delete(DirectoryModel).where(DirectoryModel.id == directory_id.value)
        )

    async def _insert(self, directory: Directory) -> None:
        try:
            await self._session.execute(
                insert(DirectoryModel).values(
                    id=directory.id.value,
                    name=directory.name,
                    code=directory.code,
                    location=directory.location.to_wkt(),
                    created_at=directory.created_at or datetime.now(UTC),
                    updated_at=directory.updated_at or datetime.now(UTC),
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Directory {directory.id} already exists",
                context=directory.id.value,
            ) from exc

    async def _update(self, directory: Directory) -> None:
        result = await self._session.execute(
            update(DirectoryModel.__table__)
            .where(DirectoryModel.id == directory.id.value)
            .where(DirectoryModel.version_id == directory.version)
            .values(
                name=directory.name,
                code=directory.code,
                location=directory.location.to_wkt(),
                updated_at=directory.updated_at or datetime.now(UTC),
                version_id=directory.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Directory {directory.id} was modified concurrently "
                f"(stale version {directory.version})",
                context=directory.id.value,
            )

    def _to_aggregate(self, row) -> Directory:


        location_obj = Location.from_wkt(row.location) if row.location else None

        return Directory(
            DirectoryId(row.id),
            name=row.name,
            code=row.code,
            location=location_obj,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
