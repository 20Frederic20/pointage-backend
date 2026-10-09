"""Read models of the time calculation context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import CalculationRuleVersion, DailyTimeResult
from ..domain.value_objects import CalculationRuleVersionId, DailyTimeResultId
from .persistence.calculation_rule_version_repository import CalculationRuleVersionRepository
from .persistence.daily_time_result_repository import DailyTimeResultRepository
from .persistence.event_sourced_calculation_rule_version_repository import (
    CALCULATION_RULE_VERSION_EVENT_TYPES,
    CALCULATION_RULE_VERSION_STREAM,
)
from .persistence.event_sourced_daily_time_result_repository import (
    DAILY_TIME_RESULT_EVENT_TYPES,
    DAILY_TIME_RESULT_STREAM,
)

TIME_CALCULATION_PROJECTIONS = [
    AggregateProjection(
        stream_type=CALCULATION_RULE_VERSION_STREAM,
        aggregate_type=CalculationRuleVersion,
        id_type=CalculationRuleVersionId,
        repository_type=CalculationRuleVersionRepository,
        event_types=CALCULATION_RULE_VERSION_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=DAILY_TIME_RESULT_STREAM,
        aggregate_type=DailyTimeResult,
        id_type=DailyTimeResultId,
        repository_type=DailyTimeResultRepository,
        event_types=DAILY_TIME_RESULT_EVENT_TYPES,
    ),
]
