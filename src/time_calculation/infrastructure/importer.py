"""One-off takeover of the time calculation state tables into the event store.

Run once when event sourcing starts (see ``scripts/import_state_to_event_store.py``):
each existing row becomes a stream holding one ``*Imported`` event with its
current state. Re-runnable: a row whose stream exists is skipped. Rule versions
go first (daily results reference them).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.event_store import EventStore

from ..domain.entities import CalculationRuleVersion, DailyTimeResult
from ..domain.events import CalculationRuleVersionImported, DailyTimeResultImported
from ..domain.value_objects import CalculationRuleVersionId, DailyTimeResultId
from .persistence.calculation_rule_version_repository import CalculationRuleVersionRepository
from .persistence.daily_time_result_repository import DailyTimeResultRepository
from .persistence.event_sourced_calculation_rule_version_repository import (
    EventSourcedCalculationRuleVersionRepository,
)
from .persistence.event_sourced_daily_time_result_repository import EventSourcedDailyTimeResultRepository
from .persistence.models import CalculationRuleVersionModel, DailyTimeResultModel


async def import_time_calculation_streams(*, state_session: AsyncSession, event_store: EventStore) -> int:
    """Import every rule version, then every daily result; returns how many streams were created."""
    return await _import_rule_versions(state_session, event_store) + await _import_daily_time_results(
        state_session, event_store
    )


async def _import_rule_versions(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = CalculationRuleVersionRepository(state_session)
    streams = EventSourcedCalculationRuleVersionRepository(event_store)
    ids = (
        await state_session.scalars(
            select(CalculationRuleVersionModel.id).order_by(
                CalculationRuleVersionModel.created_at, CalculationRuleVersionModel.id
            )
        )
    ).all()
    imported = 0
    for value in ids:
        rule_version_id = CalculationRuleVersionId(value)
        if await streams.exists(rule_version_id):
            continue
        current = await rows.get_by_id(rule_version_id)
        event = CalculationRuleVersionImported(
            rule_version_id,
            rule_version=current.rule_version,
            effective_from=current.effective_from,
            effective_to=current.effective_to,
            min_break_duration=current.min_break_duration,
            break_threshold=current.break_threshold,
            max_daily_work_duration=current.max_daily_work_duration,
            max_amplitude=current.max_amplitude,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        rule_version = CalculationRuleVersion.rehydrate(rule_version_id, [])
        rule_version.apply(event)
        rule_version.record_event(event)
        await streams.save(rule_version)
        imported += 1
    return imported


async def _import_daily_time_results(state_session: AsyncSession, event_store: EventStore) -> int:
    rows = DailyTimeResultRepository(state_session)
    streams = EventSourcedDailyTimeResultRepository(event_store)
    ids = (
        await state_session.scalars(
            select(DailyTimeResultModel.id).order_by(DailyTimeResultModel.created_at, DailyTimeResultModel.id)
        )
    ).all()
    imported = 0
    for value in ids:
        daily_time_result_id = DailyTimeResultId(value)
        if await streams.exists(daily_time_result_id):
            continue
        current = await rows.get_by_id(daily_time_result_id)
        event = DailyTimeResultImported(
            daily_time_result_id,
            employee_id=current.employee_id,
            period_id=current.period_id,
            calculation_rule_version_id=current.calculation_rule_version_id,
            work_date=current.work_date,
            planned_duration=current.planned_duration,
            worked_duration=current.worked_duration,
            break_duration=current.break_duration,
            absence_duration=current.absence_duration,
            late_duration=current.late_duration,
            status=current.status,
            calculated_at=current.calculated_at,
            created_at=current.created_at,
        )
        event.restore_identity(event.event_id, current.updated_at)
        daily_time_result = DailyTimeResult.rehydrate(daily_time_result_id, [])
        daily_time_result.apply(event)
        daily_time_result.record_event(event)
        await streams.save(daily_time_result)
        imported += 1
    return imported
