"""One-off takeover of the adjustements state tables into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing row becomes a stream holding one ``*Imported`` event with its
current state. Re-runnable: a row whose stream exists is skipped. Anomalies
go first: regularization requests reference them.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import Anomaly, RegularizationRequest
from ..domain.events import AnomalyImported, RegularizationRequestImported
from ..domain.value_objects import AnomalyId, RegularizationRequestId
from .persistence.anomaly_repository import AnomalyRepository
from .persistence.event_sourced_anomaly_repository import EventSourcedAnomalyRepository
from .persistence.event_sourced_regularization_request_repository import (
    EventSourcedRegularizationRequestRepository,
)
from .persistence.models import AnomalyModel, RegularizationRequestModel
from .persistence.regularization_request_repository import RegularizationRequestRepository


async def import_adjustements_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every anomaly then every regularization request; returns how many streams were created."""
    return await _import_anomalies(state_session, event_store) + await _import_regularization_requests(
        state_session, event_store
    )


async def _import_anomalies(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = AnomalyRepository(state_session)
    streams = EventSourcedAnomalyRepository(event_store)
    ids = (
        await state_session.scalars(select(AnomalyModel.id).order_by(AnomalyModel.created_at, AnomalyModel.id))
    ).all()
    imported = 0
    for value in ids:
        anomaly_id = AnomalyId(value)
        if await streams.exists(anomaly_id):
            continue
        current = await rows.get_by_id(anomaly_id)
        event = AnomalyImported(
            anomaly_id,
            time_entry_id=current.time_entry_id,
            type=current.type,
            severity=current.severity,
            status=current.status,
            detected_at=current.detected_at,
            resolved_at=current.resolved_at,
            description=current.description,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        anomaly = Anomaly.rehydrate(anomaly_id, [])
        anomaly.apply(event)
        anomaly.record_event(event)
        await streams.save(anomaly)
        imported += 1
    return imported


async def _import_regularization_requests(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = RegularizationRequestRepository(state_session)
    streams = EventSourcedRegularizationRequestRepository(event_store)
    ids = (
        await state_session.scalars(
            select(RegularizationRequestModel.id).order_by(
                RegularizationRequestModel.created_at, RegularizationRequestModel.id
            )
        )
    ).all()
    imported = 0
    for value in ids:
        regularization_request_id = RegularizationRequestId(value)
        if await streams.exists(regularization_request_id):
            continue
        current = await rows.get_by_id(regularization_request_id)
        event = RegularizationRequestImported(
            regularization_request_id,
            anomaly_id=current.anomaly_id,
            request_at=current.request_at,
            reason=current.reason,
            proposed_time=current.proposed_time,
            status=current.status,
            decision_comment=current.decision_comment,
            validated_at=current.validated_at,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        regularization_request = RegularizationRequest.rehydrate(regularization_request_id, [])
        regularization_request.apply(event)
        regularization_request.record_event(event)
        await streams.save(regularization_request)
        imported += 1
    return imported
