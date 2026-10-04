"""SQLAlchemy adapter for the EmployeeAssignment aggregate."""

from datetime import UTC, date, datetime

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import EmployeeAssignment
from ...domain.repositories import IEmployeeAssignmentRepository
from ...domain.value_objects.ids import DirectoryId, EmployeeAssignmentId, EmployeeId, SiteId
from .models import EmployeeAssignmentModel


def _overlaps(start_date: date, end_date: date | None):
    """Rows whose ``[start_date, end_date]`` intersects the given range (open end = forever)."""
    return (
        EmployeeAssignmentModel.start_date <= (end_date or date.max),
        or_(
            EmployeeAssignmentModel.end_date.is_(None),
            EmployeeAssignmentModel.end_date >= start_date,
        ),
    )


class EmployeeAssignmentRepository(IEmployeeAssignmentRepository):
    """Same versioned save protocol as :class:`UserRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, employee_assignment_id: EmployeeAssignmentId) -> EmployeeAssignment:
        row = await self._session.get(EmployeeAssignmentModel, employee_assignment_id.value)
        if row is None:
            raise NotFoundError(
                f"Employee assignment {employee_assignment_id.value} not found",
                context=employee_assignment_id.value,
            )
        return self._to_aggregate(row)

    async def exists(self, employee_assignment_id: EmployeeAssignmentId) -> bool:
        row = await self._session.scalar(
            select(EmployeeAssignmentModel.id).where(
                EmployeeAssignmentModel.id == employee_assignment_id.value
            )
        )
        return row is not None

    async def exists_overlapping(
        self,
        employee_id: EmployeeId,
        start_date: date,
        end_date: date | None,
        *,
        excluding: EmployeeAssignmentId | None = None,
    ) -> bool:
        stmt = select(EmployeeAssignmentModel.id).where(
            EmployeeAssignmentModel.employee_id == employee_id.value, *_overlaps(start_date, end_date)
        )
        if excluding is not None:
            stmt = stmt.where(EmployeeAssignmentModel.id != excluding.value)
        return await self._session.scalar(stmt.limit(1)) is not None

    async def find_active(self, employee_id: EmployeeId, day: date) -> EmployeeAssignment | None:
        row = await self._session.scalar(
            select(EmployeeAssignmentModel)
            .where(EmployeeAssignmentModel.employee_id == employee_id.value, *_overlaps(day, day))
            .limit(1)
        )
        return self._to_aggregate(row) if row is not None else None

    async def find_by_employee(self, employee_id: EmployeeId) -> list[EmployeeAssignment]:
        rows = await self._session.scalars(
            select(EmployeeAssignmentModel)
            .where(EmployeeAssignmentModel.employee_id == employee_id.value)
            .order_by(EmployeeAssignmentModel.start_date.desc())
        )
        return [self._to_aggregate(row) for row in rows.all()]

    async def save(self, employee_assignment: EmployeeAssignment) -> None:
        if employee_assignment.version == 0:
            await self._insert(employee_assignment)
        else:
            await self._update(employee_assignment)
        employee_assignment._advance_version()

    async def delete(self, employee_assignment_id: EmployeeAssignmentId) -> None:
        await self._session.execute(
            delete(EmployeeAssignmentModel).where(
                EmployeeAssignmentModel.id == employee_assignment_id.value
            )
        )

    async def _insert(self, employee_assignment: EmployeeAssignment) -> None:
        try:
            await self._session.execute(
                insert(EmployeeAssignmentModel).values(
                    id=employee_assignment.id.value,
                    employee_id=employee_assignment.employee_id.value,
                    directory_id=employee_assignment.directory_id.value,
                    site_id=employee_assignment.site_id.value,
                    start_date=employee_assignment.start_date,
                    end_date=employee_assignment.end_date,
                    created_at=employee_assignment.created_at or datetime.now(UTC),
                    updated_at=employee_assignment.updated_at or datetime.now(UTC),
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Employee assignment {employee_assignment.id} already exists",
                context=employee_assignment.id.value,
            ) from exc

    async def _update(self, employee_assignment: EmployeeAssignment) -> None:
        result = await self._session.execute(
            update(EmployeeAssignmentModel.__table__)
            .where(EmployeeAssignmentModel.id == employee_assignment.id.value)
            .where(EmployeeAssignmentModel.version_id == employee_assignment.version)
            .values(
                end_date=employee_assignment.end_date,
                updated_at=employee_assignment.updated_at or datetime.now(UTC),
                version_id=employee_assignment.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Employee assignment {employee_assignment.id} was modified concurrently "
                f"(stale version {employee_assignment.version})",
                context=employee_assignment.id.value,
            )

    def _to_aggregate(self, row) -> EmployeeAssignment:
        return EmployeeAssignment(
            EmployeeAssignmentId(row.id),
            employee_id=EmployeeId(row.employee_id),
            directory_id=DirectoryId(row.directory_id),
            site_id=SiteId(row.site_id),
            start_date=row.start_date,
            end_date=row.end_date,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
