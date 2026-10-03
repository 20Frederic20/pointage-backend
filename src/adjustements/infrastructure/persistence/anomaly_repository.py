from adjustements.domain import IAnomalyRepository, Anomaly, AnomalyId
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.domain.errors import NotFoundError


def _to_aggregate(row) -> Anomaly:
    return Anomaly(
        anomaly_id=AnomalyId(row.id),
        type=row.type,
        severity=row.severity,
        status=row.status,
        detected_at=row.detected_at,
        resolved_at=row.resolved_at,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version_id,
    )


class AnomalyRepository(IAnomalyRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, anomaly_id: AnomalyId) -> Anomaly:
        row = await self._session.get(Anomaly, anomaly_id.value)
        if row is None:
            raise NotFoundError(
                f"Anomaly {anomaly_id} not found",
                context=anomaly_id.value,
            )
        return _to_aggregate(row)

    async def exists(self, anomaly_id: AnomalyId) -> Anomaly:
        row = await self._session.scalar(
            select(Anomaly.id).where(Anomaly.id == anomaly_id.value)
        )
        return row is not None

    async def exists_any(self) -> bool:
        row = await self._session.scalar(select(Anomaly.id).limit(1))
        return row is not None

    async def save(self, anomaly: Anomaly) -> None:
        if anomaly.version == 0:
            await self._insert(anomaly)
        anomaly._advance_version()

    async def _insert(self, anomaly: Anomaly) -> None:
        try:
            await self._session.execute(
                Anomaly.__table__.insert().values(
                    id=anomaly.id.value,
                    type=anomaly.type,
                    severity=anomaly.severity,
                    status=anomaly.status,
                    detected_at=anomaly.detected_at,
                    resolved_at=anomaly.resolved_at,
                    description=anomaly.description,
                    created_at=anomaly.created_at,
                    updated_at=anomaly.updated_at,
                    version_id=anomaly.version
                )
            )
        except Exception as e:
            await self._session.rollback()
            raise e