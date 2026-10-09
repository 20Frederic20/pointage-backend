"""One-off takeover of the absences state tables into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing row becomes a stream holding one ``*Imported`` event with its
current state. Re-runnable: a row whose stream exists is skipped. Absence
types go first (absences reference them).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import Absence, AbsenceType
from ..domain.events import AbsenceImported, AbsenceTypeImported
from ..domain.value_objects import AbsenceId, AbsenceTypeId
from .persistence.absence_repository import AbsenceRepository
from .persistence.absence_type_repository import AbsenceTypeRepository
from .persistence.event_sourced_absence_repository import EventSourcedAbsenceRepository
from .persistence.event_sourced_absence_type_repository import EventSourcedAbsenceTypeRepository
from .persistence.models import AbsenceModel, AbsenceTypeModel


async def import_absences_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every absence type then every absence; returns how many streams were created."""
    return await _import_absence_types(state_session, event_store) + await _import_absences(
        state_session, event_store
    )


async def _import_absence_types(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = AbsenceTypeRepository(state_session)
    streams = EventSourcedAbsenceTypeRepository(event_store)
    ids = (
        await state_session.scalars(
            select(AbsenceTypeModel.id).order_by(AbsenceTypeModel.created_at, AbsenceTypeModel.id)
        )
    ).all()
    imported = 0
    for value in ids:
        absence_type_id = AbsenceTypeId(value)
        if await streams.exists(absence_type_id):
            continue
        current = await rows.get_by_id(absence_type_id)
        event = AbsenceTypeImported(
            absence_type_id,
            name=current.name,
            paid=current.paid,
            counts_as_work_time=current.counts_as_work_time,
            deducts_balance=current.deducts_balance,
            active=current.active,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        absence_type = AbsenceType.rehydrate(absence_type_id, [])
        absence_type.apply(event)
        absence_type.record_event(event)
        await streams.save(absence_type)
        imported += 1
    return imported


async def _import_absences(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = AbsenceRepository(state_session)
    streams = EventSourcedAbsenceRepository(event_store)
    ids = (
        await state_session.scalars(select(AbsenceModel.id).order_by(AbsenceModel.created_at, AbsenceModel.id))
    ).all()
    imported = 0
    for value in ids:
        absence_id = AbsenceId(value)
        if await streams.exists(absence_id):
            continue
        current = await rows.get_by_id(absence_id)
        event = AbsenceImported(
            absence_id,
            employee_id=current.employee_id,
            absence_type_id=current.absence_type_id,
            start_at=current.start_at,
            end_at=current.end_at,
            reason=current.reason,
            status=current.status,
            justification_reference=current.justification_reference,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        absence = Absence.rehydrate(absence_id, [])
        absence.apply(event)
        absence.record_event(event)
        await streams.save(absence)
        imported += 1
    return imported
