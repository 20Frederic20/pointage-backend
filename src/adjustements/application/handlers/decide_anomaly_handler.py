"""A responsible validates or rejects an anomaly.

The anomaly and its time entry change together, in one transaction: a
validated assisted punch now counts, a rejected one never will. The day
recalculation is the caller's job, once this command has committed.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot
from identity.domain import Role, UserId
from identity.domain.errors.errors import RolePermissionDeniedError
from identity.domain.repositories import IEmployeeRepository
from punch.domain.entities import TimeEntry
from punch.domain.repositories import ITimeEntryRepository

from ...domain.entities import Anomaly
from ...domain.errors import SelfDecisionError
from ...domain.repositories import IAnomalyRepository
from ...domain.value_objects import AnomalyId
from ..commands import DecideAnomalyCommand
from ..dtos import AnomalyDecisionDTO, AnomalyDTO


class DecideAnomalyHandler(CommandHandler[DecideAnomalyCommand, AnomalyDecisionDTO]):
    """Role re-checked, no self-decision, then the decision on both aggregates."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        anomaly_repository: IAnomalyRepository,
        time_entry_repository: ITimeEntryRepository,
        employee_repository: IEmployeeRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self.anomaly_repository = anomaly_repository
        self.time_entry_repository = time_entry_repository
        self.employee_repository = employee_repository

    async def _execute(self, request: DecideAnomalyCommand) -> tuple[AnomalyDecisionDTO, Sequence[AggregateRoot]]:
        actor = request.actor_user_id
        action = f"ANOMALY_{request.decision}"

        # 1. Responsible roles only (the route checks it too).
        try:
            allowed = Role(request.actor_role).at_least(Role.MANAGER)
        except ValueError:
            allowed = False
        if not allowed:
            audit.warning("action=%s user_id=%s anomaly=%s status=FAIL reason=role", action, actor, request.anomaly_id)
            raise RolePermissionDeniedError(
                f"Role {request.actor_role} cannot decide an anomaly", context=actor
            )

        # 2. The anomaly and its time entry (404 when unknown).
        anomaly = await self.anomaly_repository.get_by_id(AnomalyId(request.anomaly_id))
        time_entry = await self.time_entry_repository.get_by_id(anomaly.time_entry_id)

        # 3. Never on an anomaly where the actor is the assistant or the punched employee.
        actor_employee = await self.employee_repository.find_by_user_id(UserId(actor))
        punched = {anomaly.employee_id, time_entry.employee_id} - {None}
        if (anomaly.assisted_by_user_id is not None and anomaly.assisted_by_user_id.value == actor) or (
            actor_employee is not None and actor_employee.id in punched
        ):
            audit.warning("action=%s user_id=%s anomaly=%s status=FAIL reason=self", action, actor, request.anomaly_id)
            raise SelfDecisionError("You cannot decide an anomaly that concerns you", context=request.anomaly_id)

        # 4. The decision, anomaly first: it refuses a second decision and a
        #    missing comment before the time entry is touched.
        now = datetime.now(UTC)
        decided_by = UserId(actor)
        if request.decision == "VALIDATE":
            anomaly.validate(decided_by=decided_by, decided_at=now, comment=request.comment)
            time_entry.validate(decided_by=decided_by, decided_at=now)
        else:
            anomaly.reject(decided_by=decided_by, decided_at=now, comment=request.comment)
            time_entry.reject(decided_by=decided_by, decided_at=now)

        audit.info(
            "action=%s user_id=%s anomaly=%s time_entry=%s status=OK",
            action, actor, anomaly.id.value, time_entry.id.value,
        )
        result = AnomalyDecisionDTO(
            anomaly=AnomalyDTO.from_aggregate(anomaly),
            employee_id=time_entry.employee_id.value,
            occured_at=time_entry.occured_at,
        )
        return result, [anomaly, time_entry]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Anomaly):
            await self.anomaly_repository.save(aggregate)
        elif isinstance(aggregate, TimeEntry):
            await self.time_entry_repository.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
