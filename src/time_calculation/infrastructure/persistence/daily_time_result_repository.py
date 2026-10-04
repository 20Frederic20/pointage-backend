"""SQLAlchemy adapter for the DailyTimeResult aggregate — the versioned save
protocol (same as ``UserRepository``)."""

from datetime import date

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from identity.domain import EmployeeId
from periods.domain import PeriodId

from ...domain.entities import DailyTimeResult
from ...domain.repositories import IDailyTimeResultRepository
from ...domain.value_objects import CalculationRuleVersionId, DailyResultStatus, DailyTimeResultId
from .models import DailyTimeResultModel


class DailyTimeResultRepository(IDailyTimeResultRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, daily_time_result_id: DailyTimeResultId) -> DailyTimeResult:
        row = await self._session.get(DailyTimeResultModel, daily_time_result_id.value)
        if row is None:
            raise NotFoundError(
                f"Daily time result {daily_time_result_id.value} not found",
                context=daily_time_result_id.value,
            )
        return self._to_aggregate(row)

    async def exists(self, daily_time_result_id: DailyTimeResultId) -> bool:
        row = await self._session.scalar(
            select(DailyTimeResultModel.id).where(DailyTimeResultModel.id == daily_time_result_id.value)
        )
        return row is not None

    async def find_by_employee_and_date(self, employee_id: EmployeeId, work_date: date) -> DailyTimeResult | None:
        row = await self._session.scalar(
            select(DailyTimeResultModel).where(
                DailyTimeResultModel.employee_id == employee_id.value,
                DailyTimeResultModel.work_date == work_date,
            )
        )
        return self._to_aggregate(row) if row is not None else None

    # -- write side ---------------------------------------------------------

    async def save(self, daily_time_result: DailyTimeResult) -> None:
        if daily_time_result.version == 0:
            await self._insert(daily_time_result)
        else:
            await self._update(daily_time_result)
        daily_time_result._advance_version()

    async def delete(self, daily_time_result_id: DailyTimeResultId) -> None:
        await self._session.execute(
            delete(DailyTimeResultModel).where(DailyTimeResultModel.id == daily_time_result_id.value)
        )

    # -- helpers -------------------------------------------------------------

    async def _insert(self, daily_time_result: DailyTimeResult) -> None:
        try:
            await self._session.execute(
                insert(DailyTimeResultModel).values(
                    id=daily_time_result.id.value,
                    employee_id=daily_time_result.employee_id.value,
                    period_id=daily_time_result.period_id.value,
                    calculation_rule_version_id=daily_time_result.calculation_rule_version_id.value,
                    work_date=daily_time_result.work_date,
                    planned_duration=daily_time_result.planned_duration,
                    worked_duration=daily_time_result.worked_duration,
                    break_duration=daily_time_result.break_duration,
                    absence_duration=daily_time_result.absence_duration,
                    late_duration=daily_time_result.late_duration,
                    status=daily_time_result.status.value,
                    calculated_at=daily_time_result.calculated_at,
                    created_at=daily_time_result.created_at,
                    updated_at=daily_time_result.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"A daily time result already exists for employee {daily_time_result.employee_id.value} "
                f"on {daily_time_result.work_date}",
                context=daily_time_result.id.value,
            ) from exc

    async def _update(self, daily_time_result: DailyTimeResult) -> None:
        result = await self._session.execute(
            update(DailyTimeResultModel.__table__)
            .where(DailyTimeResultModel.id == daily_time_result.id.value)
            .where(DailyTimeResultModel.version_id == daily_time_result.version)
            .values(
                period_id=daily_time_result.period_id.value,
                calculation_rule_version_id=daily_time_result.calculation_rule_version_id.value,
                planned_duration=daily_time_result.planned_duration,
                worked_duration=daily_time_result.worked_duration,
                break_duration=daily_time_result.break_duration,
                absence_duration=daily_time_result.absence_duration,
                late_duration=daily_time_result.late_duration,
                status=daily_time_result.status.value,
                calculated_at=daily_time_result.calculated_at,
                updated_at=daily_time_result.updated_at,
                version_id=daily_time_result.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Daily time result {daily_time_result.id.value} was modified concurrently "
                f"(stale version {daily_time_result.version})",
                context=daily_time_result.id.value,
            )

    def _to_aggregate(self, row) -> DailyTimeResult:
        return DailyTimeResult(
            DailyTimeResultId(row.id),
            employee_id=EmployeeId(row.employee_id),
            period_id=PeriodId(row.period_id),
            calculation_rule_version_id=CalculationRuleVersionId(row.calculation_rule_version_id),
            work_date=row.work_date,
            planned_duration=row.planned_duration,
            worked_duration=row.worked_duration,
            break_duration=row.break_duration,
            absence_duration=row.absence_duration,
            late_duration=row.late_duration,
            status=DailyResultStatus(row.status),
            calculated_at=row.calculated_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
