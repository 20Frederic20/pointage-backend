from core.domain.events import BaseEvent

from ..value_objects import PeriodId


class PeriodOpened(BaseEvent[PeriodId]):
    """A period was opened."""

    def __init__(self, period_id: PeriodId) -> None:
        super().__init__()
        self._period_id = period_id

    def get_aggregate_id(self) -> PeriodId:
        return self._period_id

    def get_event_name(self) -> str:
        return "periods.period.opened"


class PeriodLocked(BaseEvent[PeriodId]):
    """A period was locked for closing."""

    def __init__(self, period_id: PeriodId) -> None:
        super().__init__()
        self._period_id = period_id

    def get_aggregate_id(self) -> PeriodId:
        return self._period_id

    def get_event_name(self) -> str:
        return "periods.period.locked"


class PeriodClosed(BaseEvent[PeriodId]):
    """A period was closed."""

    def __init__(self, period_id: PeriodId) -> None:
        super().__init__()
        self._period_id = period_id

    def get_aggregate_id(self) -> PeriodId:
        return self._period_id

    def get_event_name(self) -> str:
        return "periods.period.closed"
