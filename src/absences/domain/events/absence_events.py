from core.domain.events import BaseEvent

from ..value_objects import AbsenceId


class AbsenceDeclared(BaseEvent[AbsenceId]):
    """An employee declared an absence."""

    def __init__(self, absence_id: AbsenceId) -> None:
        super().__init__()
        self._absence_id = absence_id

    def get_aggregate_id(self) -> AbsenceId:
        return self._absence_id

    def get_event_name(self) -> str:
        return "absences.absence.declared"


class AbsenceApproved(BaseEvent[AbsenceId]):
    """An absence was approved."""

    def __init__(self, absence_id: AbsenceId) -> None:
        super().__init__()
        self._absence_id = absence_id

    def get_aggregate_id(self) -> AbsenceId:
        return self._absence_id

    def get_event_name(self) -> str:
        return "absences.absence.approved"


class AbsenceRejected(BaseEvent[AbsenceId]):
    """An absence was rejected."""

    def __init__(self, absence_id: AbsenceId) -> None:
        super().__init__()
        self._absence_id = absence_id

    def get_aggregate_id(self) -> AbsenceId:
        return self._absence_id

    def get_event_name(self) -> str:
        return "absences.absence.rejected"
