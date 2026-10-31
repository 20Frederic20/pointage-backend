"""One-off takeover of the punch state tables into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing row becomes a stream holding one ``*Imported`` event with its
current state. Re-runnable: a row whose stream exists is skipped.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import TimeEntry
from ..domain.events import TimeEntryImported
from ..domain.value_objects.ids import TimeEntryId
from .persistence.event_sourced_time_entry_repository import EventSourcedTimeEntryRepository
from .persistence.models import TimeEntryModel
from .persistence.time_entry_repository import TimeEntryRepository


async def import_punch_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every time entry; returns how many streams were created."""
    rows = TimeEntryRepository(state_session)
    streams = EventSourcedTimeEntryRepository(event_store)
    ids = (
        await state_session.scalars(select(TimeEntryModel.id).order_by(TimeEntryModel.created_at, TimeEntryModel.id))
    ).all()
    imported = 0
    for value in ids:
        time_entry_id = TimeEntryId(value)
        if await streams.exists(time_entry_id):
            continue
        current = await rows.get_by_id(time_entry_id)
        event = TimeEntryImported(
            time_entry_id,
            employee_id=current.employee_id,
            entry_type=current.entry_type,
            occured_at=current.occured_at,
            location=current.location,
            location_confidence=current.location_confidence,
            source=current.source,
            idempotency_key=current.idempotency_key,
            wifi_identifier=current.wifi_identifier,
            created_at=current.created_at,
            assisted_by_user_id=current.assisted_by_user_id,
            photo_key=current.photo_key,
            validation_status=current.validation_status,
        )
        event.restore_identity(event.event_id, current.updated_at)
        time_entry = TimeEntry.rehydrate(time_entry_id, [])
        time_entry.apply(event)
        time_entry.record_event(event)
        await streams.save(time_entry)
        imported += 1
    return imported
