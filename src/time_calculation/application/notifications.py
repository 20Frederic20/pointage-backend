"""Integration events of the time calculation context — the outbox wire format.

The outbox relay rehydrates by ``event_name`` from the registry, so these
names are part of the contract — do not rename them casually.
"""

import uuid
from dataclasses import dataclass

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent

from ..domain.events import CalculationRuleVersionCreated, DailyTimeResultCalculated, DailyTimeResultValidated

TIME_CALCULATION_TOPIC = "time_calculation"


@dataclass(frozen=True)
class CalculationRuleVersionCreatedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class DailyTimeResultCalculatedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class DailyTimeResultValidatedNotification(DCNotificationEvent[dict]):
    pass


def _notification(
    notification_type: type[DCNotificationEvent[dict]],
    event: BaseEvent,
    payload: dict,
) -> DCNotificationEvent[dict]:
    """Shared plumbing: base metadata plus the event's specifics."""
    return notification_type(
        event_name=event.get_event_name(),
        payload=payload,
        event_id=uuid.uuid4(),
        event_timestamp=event.occurred_at,
        topic=TIME_CALCULATION_TOPIC,
    )


def to_calculation_rule_version_created(
    event: CalculationRuleVersionCreated,
) -> CalculationRuleVersionCreatedNotification:
    return _notification(
        CalculationRuleVersionCreatedNotification,
        event,
        {"calculation_rule_version_id": event.get_aggregate_id().value},
    )


def to_daily_time_result_calculated(
    event: DailyTimeResultCalculated,
) -> DailyTimeResultCalculatedNotification:
    return _notification(
        DailyTimeResultCalculatedNotification,
        event,
        {"daily_time_result_id": event.get_aggregate_id().value},
    )


def to_daily_time_result_validated(
    event: DailyTimeResultValidated,
) -> DailyTimeResultValidatedNotification:
    return _notification(
        DailyTimeResultValidatedNotification,
        event,
        {"daily_time_result_id": event.get_aggregate_id().value},
    )


TIME_CALCULATION_EVENT_MAPPERS: dict[type, object] = {
    CalculationRuleVersionCreated: to_calculation_rule_version_created,
    DailyTimeResultCalculated: to_daily_time_result_calculated,
    DailyTimeResultValidated: to_daily_time_result_validated,
}

TIME_CALCULATION_EVENT_REGISTRY: dict[str, type] = {
    "time_calculation.calculation_rule_version.created": CalculationRuleVersionCreatedNotification,
    "time_calculation.daily_time_result.calculated": DailyTimeResultCalculatedNotification,
    "time_calculation.daily_time_result.validated": DailyTimeResultValidatedNotification,
}
