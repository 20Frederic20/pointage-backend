"""Read models of the absences context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import Absence, AbsenceType
from ..domain.value_objects import AbsenceId, AbsenceTypeId
from .persistence.absence_repository import AbsenceRepository
from .persistence.absence_type_repository import AbsenceTypeRepository
from .persistence.event_sourced_absence_repository import (
    ABSENCE_EVENT_TYPES,
    ABSENCE_STREAM,
)
from .persistence.event_sourced_absence_type_repository import (
    ABSENCE_TYPE_EVENT_TYPES,
    ABSENCE_TYPE_STREAM,
)

ABSENCES_PROJECTIONS = [
    AggregateProjection(
        stream_type=ABSENCE_TYPE_STREAM,
        aggregate_type=AbsenceType,
        id_type=AbsenceTypeId,
        repository_type=AbsenceTypeRepository,
        event_types=ABSENCE_TYPE_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=ABSENCE_STREAM,
        aggregate_type=Absence,
        id_type=AbsenceId,
        repository_type=AbsenceRepository,
        event_types=ABSENCE_EVENT_TYPES,
    ),
]
