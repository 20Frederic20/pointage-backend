"""SQLAlchemy adapter for the EmployeeSchedule aggregate — the versioned save
protocol (same as ``UserRepository``)."""

from datetime import date

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from identity.domain import EmployeeId

from ...domain.entities import EmployeeSchedule
from ...domain.repositories import IEmployeeScheduleRepository
from ...domain.value_objects import EmployeeScheduleId, TimeProfileVersionId
from .models import EmployeeScheduleModel


def _overlaps(start_date: date, end_date: date | None):
    """Rows whose ``[start_date, end_date]`` intersects the given range (open end = forever)."""
    return (
        EmployeeScheduleModel.start_date <= (end_date or date.max),
        or_(EmployeeScheduleModel.end_date.is_(None), EmployeeScheduleModel.end_date >= start_date),
    )


class EmployeeScheduleRepository(IEmployeeScheduleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, employee_schedule_id: EmployeeScheduleId) -> EmployeeSchedule:
        row = await self._session.get(EmployeeScheduleModel, employee_schedule_id.value)
        if row is None:
            raise NotFoundError(
                f"Employee schedule {employee_schedule_id.value} not found",
                context=employee_schedule_id.value,
            )
        return self._to_aggregate(row)

    async def exists(self, employee_schedule_id: EmployeeScheduleId) -> bool:
        row = await self._session.scalar(
            select(EmployeeScheduleModel.id).where(EmployeeScheduleModel.id == employee_schedule_id.value)
        )
        return row is not None

    async def exists_overlapping(
        self,
        employee_id: EmployeeId,
        start_date: date,
        end_date: date | None,
        *,
        excluding: EmployeeScheduleId | None = None,
    ) -> bool:
        stmt = select(EmployeeScheduleModel.id).where(
            EmployeeScheduleModel.employee_id == employee_id.value, *_overlaps(start_date, end_date)
        )
        if excluding is not None:
            stmt = stmt.where(EmployeeScheduleModel.id != excluding.value)
        return await self._session.scalar(stmt.limit(1)) is not None

    async def find_applicable(self, employee_id: EmployeeId, day: date) -> EmployeeSchedule | None:
        row = await self._session.scalar(
            select(EmployeeScheduleModel)
            .where(EmployeeScheduleModel.employee_id == employee_id.value, *_overlaps(day, day))
            .limit(1)
        )
        return self._to_aggregate(row) if row is not None else None

    async def find_employee_ids_between(self, start_date: date, end_date: date) -> list[EmployeeId]:
        rows = await self._session.scalars(
            select(EmployeeScheduleModel.employee_id).where(*_overlaps(start_date, end_date)).distinct()
        )
        return [EmployeeId(employee_id) for employee_id in rows.all()]

    # -- write side ---------------------------------------------------------

    async def save(self, employee_schedule: EmployeeSchedule) -> None:
        if employee_schedule.version == 0:
            await self._insert(employee_schedule)
        else:
            await self._update(employee_schedule)
        employee_schedule._advance_version()

    async def delete(self, employee_schedule_id: EmployeeScheduleId) -> None:
        await self._session.execute(
            delete(EmployeeScheduleModel).where(EmployeeScheduleModel.id == employee_schedule_id.value)
        )

    # -- helpers -------------------------------------------------------------

    async def _insert(self, employee_schedule: EmployeeSchedule) -> None:
        try:
            await self._session.execute(
                insert(EmployeeScheduleModel).values(
                    id=employee_schedule.id.value,
                    employee_id=employee_schedule.employee_id.value,
                    time_profile_version_id=employee_schedule.time_profile_version_id.value,
                    start_date=employee_schedule.start_date,
                    end_date=employee_schedule.end_date,
                    created_at=employee_schedule.created_at,
                    updated_at=employee_schedule.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Employee schedule {employee_schedule.id.value} conflicts with an existing row",
                context=employee_schedule.id.value,
            ) from exc

    async def _update(self, employee_schedule: EmployeeSchedule) -> None:
        result = await self._session.execute(
            update(EmployeeScheduleModel.__table__)
            .where(EmployeeScheduleModel.id == employee_schedule.id.value)
            .where(EmployeeScheduleModel.version_id == employee_schedule.version)
            .values(
                end_date=employee_schedule.end_date,
                updated_at=employee_schedule.updated_at,
                version_id=employee_schedule.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Employee schedule {employee_schedule.id.value} was modified concurrently "
                f"(stale version {employee_schedule.version})",
                context=employee_schedule.id.value,
            )

    def _to_aggregate(self, row) -> EmployeeSchedule:
        return EmployeeSchedule(
            EmployeeScheduleId(row.id),
            employee_id=EmployeeId(row.employee_id),
            time_profile_version_id=TimeProfileVersionId(row.time_profile_version_id),
            start_date=row.start_date,
            end_date=row.end_date,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
