"""One-off takeover of the planning state tables into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing time profile (with its versions and days) and each employee
schedule becomes a stream holding one ``*Imported`` event with its current
state. Profiles first: schedules reference their versions. Re-runnable: a row
whose stream exists is skipped.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import EmployeeSchedule, TimeProfile
from ..domain.events import EmployeeScheduleImported, TimeProfileImported
from ..domain.value_objects import EmployeeScheduleId, TimeProfileId
from .persistence.employee_schedule_repository import EmployeeScheduleRepository
from .persistence.event_sourced_employee_schedule_repository import EventSourcedEmployeeScheduleRepository
from .persistence.event_sourced_time_profile_repository import EventSourcedTimeProfileRepository
from .persistence.models import EmployeeScheduleModel, TimeProfileModel
from .persistence.time_profile_repository import TimeProfileRepository


async def import_planning_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every time profile then every employee schedule; returns how many streams were created."""
    return await _import_time_profiles(state_session, event_store) + await _import_employee_schedules(
        state_session, event_store
    )


async def _import_time_profiles(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = TimeProfileRepository(state_session)
    streams = EventSourcedTimeProfileRepository(event_store)
    ids = (
        await state_session.scalars(
            select(TimeProfileModel.id).order_by(TimeProfileModel.created_at, TimeProfileModel.id)
        )
    ).all()
    imported = 0
    for value in ids:
        time_profile_id = TimeProfileId(value)
        if await streams.exists(time_profile_id):
            continue
        current = await rows.get_by_id(time_profile_id)
        event = TimeProfileImported(
            time_profile_id,
            name=current.name,
            timezone=current.timezone,
            active=current.active,
            versions=tuple(
                {
                    "id": version.id,
                    "version": version.version,
                    "effective_from": version.effective_from,
                    "effective_to": version.effective_to,
                    "created_at": version.created_at,
                    "updated_at": version.updated_at,
                    "days": tuple(
                        {
                            "id": day.id,
                            "day_of_week": day.day_of_week,
                            "start_time": day.start_time,
                            "end_time": day.end_time,
                            "break_duration": day.break_duration,
                            "break_threshold": day.break_threshold,
                            "tolerance": day.tolerance,
                            "created_at": day.created_at,
                            "updated_at": day.updated_at,
                        }
                        for day in version.days
                    ),
                }
                for version in current.versions
            ),
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        time_profile = TimeProfile.rehydrate(time_profile_id, [])
        time_profile.apply(event)
        time_profile.record_event(event)
        await streams.save(time_profile)
        imported += 1
    return imported


async def _import_employee_schedules(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = EmployeeScheduleRepository(state_session)
    streams = EventSourcedEmployeeScheduleRepository(event_store)
    ids = (
        await state_session.scalars(
            select(EmployeeScheduleModel.id).order_by(EmployeeScheduleModel.created_at, EmployeeScheduleModel.id)
        )
    ).all()
    imported = 0
    for value in ids:
        employee_schedule_id = EmployeeScheduleId(value)
        if await streams.exists(employee_schedule_id):
            continue
        current = await rows.get_by_id(employee_schedule_id)
        event = EmployeeScheduleImported(
            employee_schedule_id,
            employee_id=current.employee_id,
            time_profile_version_id=current.time_profile_version_id,
            start_date=current.start_date,
            end_date=current.end_date,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        schedule = EmployeeSchedule.rehydrate(employee_schedule_id, [])
        schedule.apply(event)
        schedule.record_event(event)
        await streams.save(schedule)
        imported += 1
    return imported
