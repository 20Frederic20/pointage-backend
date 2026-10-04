from core.domain.events import BaseEvent

from ..value_objects import DailyTimeResultId


class DailyTimeResultCalculated(BaseEvent[DailyTimeResultId]):
    """A daily result was calculated or recalculated."""

    def __init__(self, daily_time_result_id: DailyTimeResultId) -> None:
        super().__init__()
        self._daily_time_result_id = daily_time_result_id

    def get_aggregate_id(self) -> DailyTimeResultId:
        return self._daily_time_result_id

    def get_event_name(self) -> str:
        return "time_calculation.daily_time_result.calculated"


class DailyTimeResultValidated(BaseEvent[DailyTimeResultId]):
    """A daily result was validated."""

    def __init__(self, daily_time_result_id: DailyTimeResultId) -> None:
        super().__init__()
        self._daily_time_result_id = daily_time_result_id

    def get_aggregate_id(self) -> DailyTimeResultId:
        return self._daily_time_result_id

    def get_event_name(self) -> str:
        return "time_calculation.daily_time_result.validated"
