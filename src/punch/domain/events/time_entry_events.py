from core.domain.events import BaseEvent
from punch.domain import TimeEntryId


class TimeEntryCreated(BaseEvent[TimeEntryId]):

    def __init__(self, time_entry_id: TimeEntryId) -> None:
        super().__init__()
        self._time_entry_id = time_entry_id

    def get_aggregate_id(self) -> TimeEntryId:
        return self._time_entry_id

    def get_event_name(self) -> str:
        return "punchs.time_entry.created"