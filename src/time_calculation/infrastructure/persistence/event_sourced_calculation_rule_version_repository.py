"""Event-store adapter for the CalculationRuleVersion aggregate (write side)."""

from datetime import date

from sqlalchemy import select

from core.domain.errors import NotFoundError
from core.domain.events import encode_date
from core.infrastructure.event_store import EventModel, EventStore

from ...domain.entities import CalculationRuleVersion
from ...domain.events import (
    CalculationRuleVersionClosed,
    CalculationRuleVersionCreated,
    CalculationRuleVersionImported,
)
from ...domain.repositories import ICalculationRuleVersionRepository
from ...domain.value_objects import CalculationRuleVersionId

CALCULATION_RULE_VERSION_STREAM = "time_calculation.calculation_rule_version"

CALCULATION_RULE_VERSION_EVENT_TYPES = {
    "time_calculation.calculation_rule_version.created": CalculationRuleVersionCreated,
    "time_calculation.calculation_rule_version.closed": CalculationRuleVersionClosed,
    "time_calculation.calculation_rule_version.imported": CalculationRuleVersionImported,
}

RULE_VERSION_SCOPE = "time_calculation.calculation_rule_version.rule_version"


class EventSourcedCalculationRuleVersionRepository(ICalculationRuleVersionRepository):
    """A rule version is the replay of its stream; ``rule_version`` and
    ``effective_from`` never change after creation, so lookups query the first event."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, calculation_rule_version_id: CalculationRuleVersionId) -> CalculationRuleVersion:
        events = await self._store.load(calculation_rule_version_id.value, CALCULATION_RULE_VERSION_EVENT_TYPES)
        if not events:
            raise NotFoundError(
                f"Calculation rule version {calculation_rule_version_id.value} not found",
                context=calculation_rule_version_id.value,
            )
        return CalculationRuleVersion.rehydrate(calculation_rule_version_id, events)

    async def exists(self, calculation_rule_version_id: CalculationRuleVersionId) -> bool:
        return await self._store.exists(calculation_rule_version_id.value, CALCULATION_RULE_VERSION_STREAM)

    async def find_applicable(self, day: date) -> CalculationRuleVersion | None:
        # effective_to changes (close), so filter it on the replayed state.
        stream_ids = list(
            (
                await self._store.session.scalars(
                    self._first_events()
                    .where(EventModel.payload["effective_from"].astext <= encode_date(day))
                    .order_by(EventModel.payload["rule_version"].as_integer())
                )
            ).all()
        )
        streams = await self._store.load_streams(stream_ids, CALCULATION_RULE_VERSION_EVENT_TYPES)
        for stream_id, events in streams.items():
            rule_version = CalculationRuleVersion.rehydrate(CalculationRuleVersionId(stream_id), events)
            if rule_version.is_applicable(day):
                return rule_version
        return None

    async def find_latest(self) -> CalculationRuleVersion | None:
        stream_id = await self._store.session.scalar(
            self._first_events().order_by(EventModel.payload["rule_version"].as_integer().desc()).limit(1)
        )
        return await self.get_by_id(CalculationRuleVersionId(stream_id)) if stream_id is not None else None

    def _first_events(self):
        # The first event (created / imported) carries rule_version and effective_from.
        return select(EventModel.stream_id).where(
            EventModel.stream_type == CALCULATION_RULE_VERSION_STREAM,
            EventModel.stream_version == 1,
        )

    async def save(self, calculation_rule_version: CalculationRuleVersion) -> None:
        events = calculation_rule_version.domain_events
        stream_id = calculation_rule_version.id.value
        for event in events:
            if isinstance(event, CalculationRuleVersionCreated | CalculationRuleVersionImported):
                await self._store.reserve(RULE_VERSION_SCOPE, str(event.rule_version), stream_id)
        await self._store.append(
            stream_type=CALCULATION_RULE_VERSION_STREAM,
            stream_id=stream_id,
            expected_version=calculation_rule_version.version,
            events=events,
        )
        calculation_rule_version._advance_version(len(events))

    async def delete(self, calculation_rule_version_id: CalculationRuleVersionId) -> None:
        raise NotImplementedError("Event-sourced calculation rule versions are never deleted")
