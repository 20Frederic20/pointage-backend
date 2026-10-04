from typing import Literal

from core.domain.value_objects import EntityId


class DailyTimeResultId(EntityId[Literal["daily_time_result"]]):
    ...


class CalculationRuleVersionId(EntityId[Literal["calculation_rule_version"]]):
    ...
