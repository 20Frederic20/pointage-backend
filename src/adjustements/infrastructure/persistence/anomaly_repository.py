from datetime import datetime

from adjustements.domain import IAnomalyRepository, Anomaly, AnomalyId, AnomalyStatus, Severity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, insert, select, update

from core.domain.errors import ConflictError, NotFoundError
from .models import AnomalyModel
from identity.domain import EmployeeId, UserId
from punch.domain import TimeEntryId
from punch.infrastructure.persistence.models import TimeEntryModel

_OPEN_STATUSES = (AnomalyStatus.OPEN.value, AnomalyStatus.IN_PROGRESS.value)


def _to_aggregate(row) -> Anomaly:
    return Anomaly(
        anomaly_id=AnomalyId(row.id),
        time_entry_id=TimeEntryId(row.time_entry_id),
        type=row.type,
        severity=row.severity,
        status=row.status,
        detected_at=row.detected_at,
        resolved_at=row.resolved_at,
        description=row.description,
        employee_id=EmployeeId(row.employee_id) if row.employee_id else None,
        assisted_by_user_id=UserId(row.assisted_by_user_id) if row.assisted_by_user_id else None,
        decided_by=UserId(row.decided_by) if row.decided_by else None,
        decided_at=row.decided_at,
        decision_comment=row.decision_comment,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version_id,
    )


class AnomalyRepository(IAnomalyRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, aggregate_id: AnomalyId) -> Anomaly:
        row = await self._session.get(AnomalyModel, aggregate_id.value)
        if row is None:
            raise NotFoundError(
                f"Anomaly {aggregate_id} not found",
                context=aggregate_id.value,
            )
        return _to_aggregate(row)

    async def exists(self, aggregate_id: AnomalyId) -> bool:
        row = await self._session.scalar(
            select(AnomalyModel.id).where(AnomalyModel.id == aggregate_id.value)
        )
        return row is not None

    async def exists_open_blocking_between(self, start: datetime, end: datetime) -> bool:
        row = await self._session.scalar(
            select(AnomalyModel.id)
            .where(
                AnomalyModel.severity == Severity.BLOCKING.value,
                AnomalyModel.status.in_(_OPEN_STATUSES),
                AnomalyModel.detected_at >= start,
                AnomalyModel.detected_at < end,
            )
            .limit(1)
        )
        return row is not None

    async def find_open_by_employee_between(
        self, employee_id: EmployeeId, start: datetime, end: datetime
    ) -> list[Anomaly]:
        rows = await self._session.scalars(
            select(AnomalyModel)
            .join(TimeEntryModel, TimeEntryModel.id == AnomalyModel.time_entry_id)
            .where(
                TimeEntryModel.employee_id == employee_id.value,
                AnomalyModel.status.in_(_OPEN_STATUSES),
                AnomalyModel.detected_at >= start,
                AnomalyModel.detected_at < end,
            )
        )
        return [_to_aggregate(row) for row in rows.all()]

    async def exists_any(self) -> bool:
        row = await self._session.scalar(select(AnomalyModel.id).limit(1))
        return row is not None

    async def delete(self, aggregate_id: AnomalyId) -> None:
        await self._session.execute(delete(AnomalyModel).where(AnomalyModel.id == aggregate_id.value))

    async def save(self, aggregate: Anomaly) -> None:
        if aggregate.version == 0:
            await self._insert(aggregate)
        else:
            await self._update(aggregate)
        aggregate._advance_version()

    async def _insert(self, anomaly: Anomaly) -> None:
        try:
            await self._session.execute(
                insert(AnomalyModel).values(
                    id=anomaly.id.value,
                    time_entry_id=anomaly.time_entry_id.value,
                    type=anomaly.type,
                    severity=anomaly.severity,
                    status=anomaly.status,
                    detected_at=anomaly.detected_at,
                    resolved_at=anomaly.resolved_at,
                    description=anomaly.description,
                    employee_id=anomaly.employee_id.value if anomaly.employee_id else None,
                    assisted_by_user_id=anomaly.assisted_by_user_id.value if anomaly.assisted_by_user_id else None,
                    decided_by=anomaly.decided_by.value if anomaly.decided_by else None,
                    decided_at=anomaly.decided_at,
                    decision_comment=anomaly.decision_comment,
                    created_at=anomaly.created_at,
                    updated_at=anomaly.updated_at,
                    version_id=1,
                )
            )
        except Exception as e:
            await self._session.rollback()
            raise e
    async def _update(self, anomaly: Anomaly) -> None:
        result = await self._session.execute(
            update(AnomalyModel.__table__)
            .where(AnomalyModel.id == anomaly.id.value)
            .where(AnomalyModel.version_id == anomaly.version)
            .values(
                status=anomaly.status,
                resolved_at=anomaly.resolved_at,
                description=anomaly.description,
                decided_by=anomaly.decided_by.value if anomaly.decided_by else None,
                decided_at=anomaly.decided_at,
                decision_comment=anomaly.decision_comment,
                updated_at=anomaly.updated_at,
                version_id=anomaly.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Anomaly {anomaly.id} was modified concurrently (stale version {anomaly.version})",
                context=anomaly.id.value,
            )
