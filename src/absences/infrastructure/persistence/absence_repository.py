"""SQLAlchemy adapter for the Absence aggregate — the versioned save protocol
(same as ``UserRepository``)."""

from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from identity.domain import EmployeeId

from ...domain.entities import Absence
from ...domain.repositories import IAbsenceRepository
from ...domain.value_objects import AbsenceId, AbsenceStatus, AbsenceTypeId
from .models import AbsenceModel


class AbsenceRepository(IAbsenceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, absence_id: AbsenceId) -> Absence:
        row = await self._session.get(AbsenceModel, absence_id.value)
        if row is None:
            raise NotFoundError(
                f"Absence {absence_id.value} not found", context=absence_id.value
            )
        return self._to_aggregate(row)

    async def exists(self, absence_id: AbsenceId) -> bool:
        row = await self._session.scalar(
            select(AbsenceModel.id).where(AbsenceModel.id == absence_id.value)
        )
        return row is not None

    async def find_approved_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[Absence]:
        rows = await self._session.scalars(
            select(AbsenceModel).where(
                AbsenceModel.employee_id == employee_id.value,
                AbsenceModel.status == AbsenceStatus.APPROVED.value,
                AbsenceModel.start_at < end,
                AbsenceModel.end_at > start,
            )
        )
        return [self._to_aggregate(row) for row in rows.all()]

    # -- write side ---------------------------------------------------------

    async def save(self, absence: Absence) -> None:
        if absence.version == 0:
            await self._insert(absence)
        else:
            await self._update(absence)
        absence._advance_version()

    async def delete(self, absence_id: AbsenceId) -> None:
        await self._session.execute(
            delete(AbsenceModel).where(AbsenceModel.id == absence_id.value)
        )

    # -- helpers -------------------------------------------------------------

    async def _insert(self, absence: Absence) -> None:
        try:
            await self._session.execute(
                insert(AbsenceModel).values(
                    id=absence.id.value,
                    employee_id=absence.employee_id.value,
                    absence_type_id=absence.absence_type_id.value,
                    start_at=absence.start_at,
                    end_at=absence.end_at,
                    reason=absence.reason,
                    status=absence.status.value,
                    justification_reference=absence.justification_reference,
                    created_at=absence.created_at,
                    updated_at=absence.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Absence {absence.id.value} conflicts with an existing row",
                context=absence.id.value,
            ) from exc

    async def _update(self, absence: Absence) -> None:
        result = await self._session.execute(
            update(AbsenceModel.__table__)
            .where(AbsenceModel.id == absence.id.value)
            .where(AbsenceModel.version_id == absence.version)
            .values(
                employee_id=absence.employee_id.value,
                absence_type_id=absence.absence_type_id.value,
                start_at=absence.start_at,
                end_at=absence.end_at,
                reason=absence.reason,
                status=absence.status.value,
                justification_reference=absence.justification_reference,
                updated_at=absence.updated_at,
                version_id=absence.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Absence {absence.id.value} was modified concurrently "
                f"(stale version {absence.version})",
                context=absence.id.value,
            )

    def _to_aggregate(self, row) -> Absence:
        return Absence(
            AbsenceId(row.id),
            employee_id=EmployeeId(row.employee_id),
            absence_type_id=AbsenceTypeId(row.absence_type_id),
            start_at=row.start_at,
            end_at=row.end_at,
            reason=row.reason,
            status=AbsenceStatus(row.status),
            justification_reference=row.justification_reference,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
