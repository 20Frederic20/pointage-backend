"""Read models of the punch context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import TimeEntry
from ..domain.value_objects.ids import TimeEntryId
from .persistence.event_sourced_time_entry_repository import TIME_ENTRY_EVENT_TYPES, TIME_ENTRY_STREAM
from .persistence.time_entry_repository import TimeEntryRepository

PUNCHES_PROJECTIONS = [
    AggregateProjection(
        stream_type=TIME_ENTRY_STREAM,
        aggregate_type=TimeEntry,
        id_type=TimeEntryId,
        repository_type=TimeEntryRepository,
        event_types=TIME_ENTRY_EVENT_TYPES,
    ),
]
