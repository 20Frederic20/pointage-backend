"""One-off takeover of the users state tables into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing row becomes a stream holding one ``*Imported`` event with its
current state. Re-runnable: a row whose stream exists is skipped. Parents
first (directories, users, sites, employees, assignments), so the projection
replays them in an order the read database's foreign keys accept.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import Directory, Employee, EmployeeAssignment, Site, User
from ..domain.events import (
    DirectoryImported,
    EmployeeAssignmentImported,
    EmployeeImported,
    SiteImported,
    UserImported,
)
from ..domain.value_objects.ids import (
    DirectoryId,
    EmployeeAssignmentId,
    EmployeeId,
    SiteId,
    UserId,
)
from .persistence.directory_repository import DirectoryRepository
from .persistence.employee_assignment_repository import EmployeeAssignmentRepository
from .persistence.employee_repository import EmployeeRepository
from .persistence.event_sourced_directory_repository import (
    EventSourcedDirectoryRepository,
)
from .persistence.event_sourced_employee_assignment_repository import (
    EventSourcedEmployeeAssignmentRepository,
)
from .persistence.event_sourced_employee_repository import (
    EventSourcedEmployeeRepository,
)
from .persistence.event_sourced_site_repository import EventSourcedSiteRepository
from .persistence.event_sourced_user_repository import EventSourcedUserRepository
from .persistence.models import (
    DirectoryModel,
    EmployeeAssignmentModel,
    EmployeeModel,
    SiteModel,
    UserModel,
)
from .persistence.site_repository import SiteRepository
from .persistence.user_repository import UserRepository


async def _ids(session: AsyncSession, model) -> list[str]:
    return list((await session.scalars(select(model.id).order_by(model.created_at, model.id))).all())


def _imported(aggregate_type, aggregate_id, event, updated_at):
    """A blank aggregate holding ``event`` as its pending first event."""
    event.restore_identity(event.event_id, updated_at)
    aggregate = aggregate_type.rehydrate(aggregate_id, [])
    aggregate.apply(event)
    aggregate.record_event(event)
    return aggregate


async def import_identity_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every directory, user, site, employee and assignment; returns how many streams were created."""
    imported = 0

    rows, streams = DirectoryRepository(state_session), EventSourcedDirectoryRepository(event_store)
    for value in await _ids(state_session, DirectoryModel):
        directory_id = DirectoryId(value)
        if await streams.exists(directory_id):
            continue
        current = await rows.get_by_id(directory_id)
        event = DirectoryImported(
            directory_id,
            code=current.code,
            name=current.name,
            parent_directory_id=current.parent_directory_id,
            created_at=current.created_at,
        )
        await streams.save(_imported(Directory, directory_id, event, current.updated_at))
        imported += 1

    rows, streams = UserRepository(state_session), EventSourcedUserRepository(event_store)
    for value in await _ids(state_session, UserModel):
        user_id = UserId(value)
        if await streams.exists(user_id):
            continue
        current = await rows.get_by_id(user_id)
        event = UserImported(
            user_id,
            email=current.email,
            password_hash=current.password_hash,
            role=current.role,
            first_name=current.first_name,
            last_name=current.last_name,
            avatar_url=current.avatar_url,
            is_active=current.is_active,
            last_active_at=current.last_active_at,
            created_at=current.created_at,
        )
        await streams.save(_imported(User, user_id, event, current.updated_at))
        imported += 1

    rows, streams = SiteRepository(state_session), EventSourcedSiteRepository(event_store)
    for value in await _ids(state_session, SiteModel):
        site_id = SiteId(value)
        if await streams.exists(site_id):
            continue
        current = await rows.get_by_id(site_id)
        event = SiteImported(
            site_id,
            directory_id=current.directory_id,
            name=current.name,
            location=current.location,
            kind=current.kind,
            address=current.address,
            active=current.active,
            created_at=current.created_at,
        )
        await streams.save(_imported(Site, site_id, event, current.updated_at))
        imported += 1

    rows, streams = EmployeeRepository(state_session), EventSourcedEmployeeRepository(event_store)
    for value in await _ids(state_session, EmployeeModel):
        employee_id = EmployeeId(value)
        if await streams.exists(employee_id):
            continue
        current = await rows.get_by_id(employee_id)
        event = EmployeeImported(
            employee_id,
            user_id=current.user_id,
            employee_number=current.employee_number,
            is_active=current.is_active,
            phone=current.phone,
            role=current.role,
            created_at=current.created_at,
        )
        await streams.save(_imported(Employee, employee_id, event, current.updated_at))
        imported += 1

    rows, streams = EmployeeAssignmentRepository(state_session), EventSourcedEmployeeAssignmentRepository(event_store)
    for value in await _ids(state_session, EmployeeAssignmentModel):
        assignment_id = EmployeeAssignmentId(value)
        if await streams.exists(assignment_id):
            continue
        current = await rows.get_by_id(assignment_id)
        event = EmployeeAssignmentImported(
            assignment_id,
            employee_id=current.employee_id,
            directory_id=current.directory_id,
            site_id=current.site_id,
            start_date=current.start_date,
            end_date=current.end_date,
            created_at=current.created_at,
        )
        await streams.save(_imported(EmployeeAssignment, assignment_id, event, current.updated_at))
        imported += 1

    return imported
