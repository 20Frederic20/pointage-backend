"""SQLAlchemy adapter for the AbsenceType aggregate — the versioned save protocol
(same as ``UserRepository``)."""

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import AbsenceType
from ...domain.repositories import IAbsenceTypeRepository
from ...domain.value_objects import AbsenceTypeId
from .models import AbsenceTypeModel


class AbsenceTypeRepository(IAbsenceTypeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, absence_type_id: AbsenceTypeId) -> AbsenceType:
        row = await self._session.get(AbsenceTypeModel, absence_type_id.value)
        if row is None:
            raise NotFoundError(
                f"Absence type {absence_type_id.value} not found", context=absence_type_id.value
            )
        return self._to_aggregate(row)

    async def exists(self, absence_type_id: AbsenceTypeId) -> bool:
        row = await self._session.scalar(
            select(AbsenceTypeModel.id).where(AbsenceTypeModel.id == absence_type_id.value)
        )
        return row is not None

    # -- write side ---------------------------------------------------------

    async def save(self, absence_type: AbsenceType) -> None:
        if absence_type.version == 0:
            await self._insert(absence_type)
        else:
            await self._update(absence_type)
        absence_type._advance_version()

    async def delete(self, absence_type_id: AbsenceTypeId) -> None:
        await self._session.execute(
            delete(AbsenceTypeModel).where(AbsenceTypeModel.id == absence_type_id.value)
        )

    # -- helpers -------------------------------------------------------------

    async def _insert(self, absence_type: AbsenceType) -> None:
        try:
            await self._session.execute(
                insert(AbsenceTypeModel).values(
                    id=absence_type.id.value,
                    name=absence_type.name,
                    paid=absence_type.paid,
                    counts_as_work_time=absence_type.counts_as_work_time,
                    deducts_balance=absence_type.deducts_balance,
                    active=absence_type.active,
                    created_at=absence_type.created_at,
                    updated_at=absence_type.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Absence type {absence_type.id.value} conflicts with an existing row",
                context=absence_type.id.value,
            ) from exc

    async def _update(self, absence_type: AbsenceType) -> None:
        result = await self._session.execute(
            update(AbsenceTypeModel.__table__)
            .where(AbsenceTypeModel.id == absence_type.id.value)
            .where(AbsenceTypeModel.version_id == absence_type.version)
            .values(
                name=absence_type.name,
                paid=absence_type.paid,
                counts_as_work_time=absence_type.counts_as_work_time,
                deducts_balance=absence_type.deducts_balance,
                active=absence_type.active,
                updated_at=absence_type.updated_at,
                version_id=absence_type.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Absence type {absence_type.id.value} was modified concurrently "
                f"(stale version {absence_type.version})",
                context=absence_type.id.value,
            )

    def _to_aggregate(self, row) -> AbsenceType:
        return AbsenceType(
            AbsenceTypeId(row.id),
            name=row.name,
            paid=row.paid,
            counts_as_work_time=row.counts_as_work_time,
            deducts_balance=row.deducts_balance,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
