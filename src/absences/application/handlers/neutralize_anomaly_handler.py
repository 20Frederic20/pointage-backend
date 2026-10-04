"""Resolve an anomaly covered by an approved absence (``neutraliserAnomalie``)."""

from collections.abc import Sequence

from adjustements.domain.entities import Anomaly
from adjustements.domain.repositories import IAnomalyRepository
from adjustements.domain.value_objects import AnomalyId
from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from punch.domain.repositories import ITimeEntryRepository

from ...domain.repositories import IAbsenceRepository
from ...domain.value_objects import AbsenceId
from ..commands import NeutralizeAnomalyCommand


class NeutralizeAnomalyHandler(CommandHandler[NeutralizeAnomalyCommand, None]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        absence_repository: IAbsenceRepository,
        anomaly_repository: IAnomalyRepository,
        time_entry_repository: ITimeEntryRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._absences = absence_repository
        self._anomalies = anomaly_repository
        self._time_entries = time_entry_repository

    async def _execute(
        self, request: NeutralizeAnomalyCommand
    ) -> tuple[None, Sequence[AggregateRoot]]:
        absence = await self._absences.get_by_id(AbsenceId(request.absence_id))
        anomaly = await self._anomalies.get_by_id(AnomalyId(request.anomaly_id))
        # The anomaly's employee is read from its time entry until anomalies
        # carry their own employee_id (Employee "1" -- "0..*" Anomaly).
        time_entry = await self._time_entries.get_by_id(anomaly.time_entry_id)

        absence.neutralize_anomaly(anomaly, anomaly_employee_id=time_entry.employee_id)
        return None, [anomaly]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Anomaly):
            await self._anomalies.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
