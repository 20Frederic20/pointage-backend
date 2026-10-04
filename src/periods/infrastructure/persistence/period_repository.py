"""SQLAlchemy adapter for the Period aggregate — the versioned save protocol
(same as ``UserRepository``)."""

from datetime import date

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import Period
from ...domain.repositories import IPeriodRepository
from ...domain.value_objects import PeriodId, PeriodStatus
from .models import PeriodModel


class PeriodRepository(IPeriodRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, period_id: PeriodId) -> Period:
        row = await self._session.get(PeriodModel, period_id.value)
        if row is None:
            raise NotFoundError(f"Period {period_id.value} not found", context=period_id.value)
        return self._to_aggregate(row)

    async def exists(self, period_id: PeriodId) -> bool:
        row = await self._session.scalar(select(PeriodModel.id).where(PeriodModel.id == period_id.value))
        return row is not None

    async def exists_overlapping(self, start_date: date, end_date: date) -> bool:
        row = await self._session.scalar(
            select(PeriodModel.id)
            .where(PeriodModel.start_date <= end_date, PeriodModel.end_date >= start_date)
            .limit(1)
        )
        return row is not None

    async def find_containing(self, day: date) -> Period | None:
        row = await self._session.scalar(
            select(PeriodModel).where(PeriodModel.start_date <= day, PeriodModel.end_date >= day).limit(1)
        )
        return self._to_aggregate(row) if row is not None else None

    # -- write side ---------------------------------------------------------

    async def save(self, period: Period) -> None:
        if period.version == 0:
            await self._insert(period)
        else:
            await self._update(period)
        period._advance_version()

    async def delete(self, period_id: PeriodId) -> None:
        await self._session.execute(delete(PeriodModel).where(PeriodModel.id == period_id.value))

    # -- helpers -------------------------------------------------------------

    async def _insert(self, period: Period) -> None:
        try:
            await self._session.execute(
                insert(PeriodModel).values(
                    id=period.id.value,
                    start_date=period.start_date,
                    end_date=period.end_date,
                    status=period.status.value,
                    closed_at=period.closed_at,
                    created_at=period.created_at,
                    updated_at=period.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Period {period.id.value} conflicts with an existing row", context=period.id.value
            ) from exc

    async def _update(self, period: Period) -> None:
        result = await self._session.execute(
            update(PeriodModel.__table__)
            .where(PeriodModel.id == period.id.value)
            .where(PeriodModel.version_id == period.version)
            .values(
                status=period.status.value,
                closed_at=period.closed_at,
                updated_at=period.updated_at,
                version_id=period.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Period {period.id.value} was modified concurrently (stale version {period.version})",
                context=period.id.value,
            )

    def _to_aggregate(self, row) -> Period:
        return Period(
            PeriodId(row.id),
            start_date=row.start_date,
            end_date=row.end_date,
            status=PeriodStatus(row.status),
            closed_at=row.closed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
