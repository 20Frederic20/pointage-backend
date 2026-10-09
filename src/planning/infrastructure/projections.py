"""Read models of the planning context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import EmployeeSchedule, TimeProfile
from ..domain.value_objects import EmployeeScheduleId, TimeProfileId
from .persistence.employee_schedule_repository import EmployeeScheduleRepository
from .persistence.event_sourced_employee_schedule_repository import (
    EMPLOYEE_SCHEDULE_EVENT_TYPES,
    EMPLOYEE_SCHEDULE_STREAM,
)
from .persistence.event_sourced_time_profile_repository import TIME_PROFILE_EVENT_TYPES, TIME_PROFILE_STREAM
from .persistence.time_profile_repository import TimeProfileRepository

PLANNING_PROJECTIONS = [
    AggregateProjection(
        stream_type=TIME_PROFILE_STREAM,
        aggregate_type=TimeProfile,
        id_type=TimeProfileId,
        repository_type=TimeProfileRepository,
        event_types=TIME_PROFILE_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=EMPLOYEE_SCHEDULE_STREAM,
        aggregate_type=EmployeeSchedule,
        id_type=EmployeeScheduleId,
        repository_type=EmployeeScheduleRepository,
        event_types=EMPLOYEE_SCHEDULE_EVENT_TYPES,
    ),
]
