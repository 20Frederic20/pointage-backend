from datetime import date, datetime

from core.domain.events import BaseEvent, decode_date, decode_datetime, encode_date, encode_datetime

from ..value_objects import PeriodId, PeriodStatus


class PeriodOpened(BaseEvent[PeriodId]):
    """A period was opened."""

    def __init__(self, period_id: PeriodId, *, start_date: date, end_date: date) -> None:
        super().__init__()
        self.period_id = period_id
        self.start_date = start_date
        self.end_date = end_date

    def get_aggregate_id(self) -> PeriodId:
        return self.period_id

    def get_event_name(self) -> str:
        return "periods.period.opened"

    def to_payload(self) -> dict:
        return {
            "period_id": self.period_id.value,
            "start_date": encode_date(self.start_date),
            "end_date": encode_date(self.end_date),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "PeriodOpened":
        return cls(
            PeriodId(payload["period_id"]),
            start_date=decode_date(payload["start_date"]),
            end_date=decode_date(payload["end_date"]),
        )


class PeriodLocked(BaseEvent[PeriodId]):
    """A period was locked for closing."""

    def __init__(self, period_id: PeriodId) -> None:
        super().__init__()
        self.period_id = period_id

    def get_aggregate_id(self) -> PeriodId:
        return self.period_id

    def get_event_name(self) -> str:
        return "periods.period.locked"

    def to_payload(self) -> dict:
        return {"period_id": self.period_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "PeriodLocked":
        return cls(PeriodId(payload["period_id"]))


class PeriodClosed(BaseEvent[PeriodId]):
    """A period was closed."""

    def __init__(self, period_id: PeriodId, *, closed_at: datetime) -> None:
        super().__init__()
        self.period_id = period_id
        self.closed_at = closed_at

    def get_aggregate_id(self) -> PeriodId:
        return self.period_id

    def get_event_name(self) -> str:
        return "periods.period.closed"

    def to_payload(self) -> dict:
        return {"period_id": self.period_id.value, "closed_at": encode_datetime(self.closed_at)}

    @classmethod
    def from_payload(cls, payload: dict) -> "PeriodClosed":
        return cls(PeriodId(payload["period_id"]), closed_at=decode_datetime(payload["closed_at"]))


class PeriodImported(BaseEvent[PeriodId]):
    """A period taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        period_id: PeriodId,
        *,
        start_date: date,
        end_date: date,
        status: PeriodStatus,
        closed_at: datetime | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.period_id = period_id
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.closed_at = closed_at
        self.created_at = created_at

    def get_aggregate_id(self) -> PeriodId:
        return self.period_id

    def get_event_name(self) -> str:
        return "periods.period.imported"

    def to_payload(self) -> dict:
        return {
            "period_id": self.period_id.value,
            "start_date": encode_date(self.start_date),
            "end_date": encode_date(self.end_date),
            "status": self.status.value,
            "closed_at": encode_datetime(self.closed_at),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "PeriodImported":
        return cls(
            PeriodId(payload["period_id"]),
            start_date=decode_date(payload["start_date"]),
            end_date=decode_date(payload["end_date"]),
            status=PeriodStatus(payload["status"]),
            closed_at=decode_datetime(payload["closed_at"]),
            created_at=decode_datetime(payload["created_at"]),
        )
