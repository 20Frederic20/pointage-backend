"""Punch rules shared by every way of punching (own phone, assisted, manager).

Each rule raises the domain error the caller audits; none of them writes.
"""

from datetime import UTC, datetime

from identity.domain import EmployeeId
from identity.domain.entities import Employee, Site
from identity.domain.repositories import IEmployeeAssignmentRepository, ISiteRepository
from identity.domain.value_objects.location import Location
from punch.domain import EntryType
from punch.domain.errors import EmployeeNotAssignedError, TooFarFromWorkplaceError
from punch.domain.repositories import ITimeEntryRepository
from punch.domain.services.distance_calculator import DistanceCalculator
from punch.domain.services.entry_type_resolver import EntryTypeResolver

MAX_DISTANCE_METERS = 500


async def resolve_today_site(
    employee: Employee,
    assignment_repo: IEmployeeAssignmentRepository,
    site_repo: ISiteRepository,
) -> Site:
    """The site of the assignment covering today; ``EmployeeNotAssignedError`` without one."""
    assignment = await assignment_repo.find_active(employee.id, datetime.now(UTC).date())
    if assignment is None:
        raise EmployeeNotAssignedError(
            f"Employee {employee.employee_number} has no active assignment today",
            context=employee.id.value,
        )
    return await site_repo.get_by_id(assignment.site_id)


def ensure_within_site(location: Location, site: Site, *, employee_id: EmployeeId | None = None) -> float:
    """Distance in metres to ``site``; ``TooFarFromWorkplaceError`` beyond ``MAX_DISTANCE_METERS``."""
    distance = DistanceCalculator.calculate(
        latitude_1=location.latitude,
        longitude_1=location.longitude,
        latitude_2=site.location.latitude,
        longitude_2=site.location.longitude,
    )
    if distance > MAX_DISTANCE_METERS:
        who = f"Employee {employee_id}" if employee_id is not None else "The punch"
        raise TooFarFromWorkplaceError(
            f"{who} is {distance:.0f} m from the workplace (max {MAX_DISTANCE_METERS} m)",
            context=employee_id.value if employee_id is not None else site.id.value,
            distance_meters=distance,
        )
    return distance


async def next_entry_type(employee_id: EmployeeId, time_entry_repo: ITimeEntryRepository, now: datetime) -> EntryType:
    """IN or OUT from the employee's last entry that was not rejected."""
    last_entry = await time_entry_repo.find_last_by_employee_id(employee_id)
    return EntryTypeResolver.resolve(last_entry, now)
