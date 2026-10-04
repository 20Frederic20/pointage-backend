from core.domain.events import BaseEvent

from ..value_objects import CalculationRuleVersionId


class CalculationRuleVersionCreated(BaseEvent[CalculationRuleVersionId]):
    """A new calculation rule version was created."""

    def __init__(self, calculation_rule_version_id: CalculationRuleVersionId) -> None:
        super().__init__()
        self._calculation_rule_version_id = calculation_rule_version_id

    def get_aggregate_id(self) -> CalculationRuleVersionId:
        return self._calculation_rule_version_id

    def get_event_name(self) -> str:
        return "time_calculation.calculation_rule_version.created"
