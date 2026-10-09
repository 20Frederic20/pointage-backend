"""One-off takeover of the periods state table into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing row becomes a stream holding one ``PeriodImported`` event with its
current state. Re-runnable: a row whose stream exists is skipped.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import Period
from ..domain.events import PeriodImported
from ..domain.value_objects import PeriodId
from .persistence.event_sourced_period_repository import EventSourcedPeriodRepository
from .persistence.models import PeriodModel
from .persistence.period_repository import PeriodRepository


async def import_periods_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every period; returns how many streams were created."""
    rows = PeriodRepository(state_session)
    streams = EventSourcedPeriodRepository(event_store)
    ids = (
        await state_session.scalars(select(PeriodModel.id).order_by(PeriodModel.created_at, PeriodModel.id))
    ).all()
    imported = 0
    for value in ids:
        period_id = PeriodId(value)
        if await streams.exists(period_id):
            continue
        current = await rows.get_by_id(period_id)
        event = PeriodImported(
            period_id,
            start_date=current.start_date,
            end_date=current.end_date,
            status=current.status,
            closed_at=current.closed_at,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        period = Period.rehydrate(period_id, [])
        period.apply(event)
        period.record_event(event)
        await streams.save(period)
        imported += 1
    return imported
