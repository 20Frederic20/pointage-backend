from datetime import UTC, date, datetime

from core.domain.entity import AggregateRoot

from ..errors import (
    InvalidPeriodDatesError,
    PeriodAlreadyClosedError,
    PeriodHasBlockingAnomaliesError,
    PeriodNotOpenError,
)
from ..events import PeriodClosed, PeriodImported, PeriodLocked, PeriodOpened
from ..value_objects import PeriodId, PeriodStatus


class Period(AggregateRoot[PeriodId]):
    """A payroll period ``[start_date, end_date]``: OPEN, then CLOSING (locked), then CLOSED."""

    __slots__ = ("_closed_at", "_end_date", "_start_date", "_status")

    def __init__(
        self,
        period_id: PeriodId,
        *,
        start_date: date,
        end_date: date,
        status: PeriodStatus = PeriodStatus.OPEN,
        closed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(period_id, created_at=created_at, updated_at=updated_at, version=version)
        if end_date < start_date:
            raise InvalidPeriodDatesError(
                f"Period ends ({end_date}) before it starts ({start_date})",
                context=period_id.value,
            )
        self._start_date = start_date
        self._end_date = end_date
        self._status = PeriodStatus(status)
        self._closed_at = closed_at

    @classmethod
    def open(cls, period_id: PeriodId, *, start_date: date, end_date: date) -> "Period":
        if end_date < start_date:
            raise InvalidPeriodDatesError(
                f"Period ends ({end_date}) before it starts ({start_date})",
                context=period_id.value,
            )
        period = cls.rehydrate(period_id, [])
        period._raise(PeriodOpened(period_id, start_date=start_date, end_date=end_date))
        return period

    def _apply(self, event) -> None:
        match event:
            case PeriodOpened():
                self._start_date = event.start_date
                self._end_date = event.end_date
                self._status = PeriodStatus.OPEN
                self._closed_at = None
            case PeriodLocked():
                self._status = PeriodStatus.CLOSING
            case PeriodClosed():
                self._status = PeriodStatus.CLOSED
                self._closed_at = event.closed_at
            case PeriodImported():
                self._start_date = event.start_date
                self._end_date = event.end_date
                self._status = event.status
                self._closed_at = event.closed_at
                self._created_at = event.created_at
            case _:
                super()._apply(event)

    def contains(self, day: date) -> bool:
        return self._start_date <= day <= self._end_date

    def lock(self) -> None:
        """``verrouiller``: freeze the period before closing it."""
        if self._status != PeriodStatus.OPEN:
            raise PeriodNotOpenError(f"Period is {self._status}, not OPEN", context=self.id.value)
        self._raise(PeriodLocked(self.id))

    def can_be_closed(self, *, has_open_blocking_anomalies: bool) -> bool:
        """``peutEtreCloturee``."""
        return not self.is_closed() and not has_open_blocking_anomalies

    def close(self, *, has_open_blocking_anomalies: bool) -> None:
        """``cloturer``: only once no blocking anomaly is left open."""
        if self.is_closed():
            raise PeriodAlreadyClosedError("Period is already closed", context=self.id.value)
        if has_open_blocking_anomalies:
            raise PeriodHasBlockingAnomaliesError(
                "Period still has open blocking anomalies", context=self.id.value
            )
        self._raise(PeriodClosed(self.id, closed_at=datetime.now(UTC)))

    def is_closed(self) -> bool:
        """``estCloturee``."""
        return self._status == PeriodStatus.CLOSED

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date:
        return self._end_date

    @property
    def status(self) -> PeriodStatus:
        return self._status

    @property
    def closed_at(self) -> datetime | None:
        return self._closed_at
