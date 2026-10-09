"""Read models of the users context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import Directory, Employee, EmployeeAssignment, Site, User
from ..domain.value_objects.ids import DirectoryId, EmployeeAssignmentId, EmployeeId, SiteId, UserId
from .persistence.directory_repository import DirectoryRepository
from .persistence.employee_assignment_repository import EmployeeAssignmentRepository
from .persistence.employee_repository import EmployeeRepository
from .persistence.event_sourced_directory_repository import DIRECTORY_EVENT_TYPES, DIRECTORY_STREAM
from .persistence.event_sourced_employee_assignment_repository import (
    EMPLOYEE_ASSIGNMENT_EVENT_TYPES,
    EMPLOYEE_ASSIGNMENT_STREAM,
)
from .persistence.event_sourced_employee_repository import EMPLOYEE_EVENT_TYPES, EMPLOYEE_STREAM
from .persistence.event_sourced_site_repository import SITE_EVENT_TYPES, SITE_STREAM
from .persistence.event_sourced_user_repository import USER_EVENT_TYPES, USER_STREAM
from .persistence.site_repository import SiteRepository
from .persistence.user_repository import UserRepository

USERS_PROJECTIONS = [
    AggregateProjection(
        stream_type=DIRECTORY_STREAM,
        aggregate_type=Directory,
        id_type=DirectoryId,
        repository_type=DirectoryRepository,
        event_types=DIRECTORY_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=USER_STREAM,
        aggregate_type=User,
        id_type=UserId,
        repository_type=UserRepository,
        event_types=USER_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=SITE_STREAM,
        aggregate_type=Site,
        id_type=SiteId,
        repository_type=SiteRepository,
        event_types=SITE_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=EMPLOYEE_STREAM,
        aggregate_type=Employee,
        id_type=EmployeeId,
        repository_type=EmployeeRepository,
        event_types=EMPLOYEE_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=EMPLOYEE_ASSIGNMENT_STREAM,
        aggregate_type=EmployeeAssignment,
        id_type=EmployeeAssignmentId,
        repository_type=EmployeeAssignmentRepository,
        event_types=EMPLOYEE_ASSIGNMENT_EVENT_TYPES,
    ),
]
