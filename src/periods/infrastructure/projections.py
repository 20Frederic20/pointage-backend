"""Read models of the periods context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import Period
from ..domain.value_objects import PeriodId
from .persistence.event_sourced_period_repository import PERIOD_EVENT_TYPES, PERIOD_STREAM
from .persistence.period_repository import PeriodRepository

PERIODS_PROJECTIONS = [
    AggregateProjection(
        stream_type=PERIOD_STREAM,
        aggregate_type=Period,
        id_type=PeriodId,
        repository_type=PeriodRepository,
        event_types=PERIOD_EVENT_TYPES,
    ),
]
