"""Read side of the back-office anomaly list (read database).

One row per anomaly, joined with its time entry, the punched employee and
their user, and the assistant's user. Outer joins: a projection that lags
(or an old anomaly without employee / assistant) leaves the columns empty
instead of hiding the anomaly.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from identity.infrastructure.persistence.models import EmployeeModel, UserModel
from punch.infrastructure.persistence.models import TimeEntryModel

from ...application.dtos import AnomalyListItemDTO
from ...domain.value_objects import AnomalyStatus, AnomalyType, Severity
from .models import AnomalyModel

_punched_user = aliased(UserModel, name="punched_user")
_assistant_user = aliased(UserModel, name="assistant_user")


class AnomalyReadRepository:
    """``IAnomalyReadRepository`` over the read database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(
        self,
        *,
        status: AnomalyStatus | None = None,
        type: AnomalyType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AnomalyListItemDTO]:
        statement = (
            self._filtered(self._items(), status, type)
            .order_by(AnomalyModel.detected_at.desc(), AnomalyModel.id)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).all()
        return [self._to_dto(row) for row in rows]

    async def count(self, *, status: AnomalyStatus | None = None, type: AnomalyType | None = None) -> int:
        statement = self._filtered(select(func.count()).select_from(AnomalyModel), status, type)
        return int(await self._session.scalar(statement) or 0)

    async def get(self, anomaly_id: str) -> AnomalyListItemDTO | None:
        row = (await self._session.execute(self._items().where(AnomalyModel.id == anomaly_id))).first()
        return self._to_dto(row) if row is not None else None

    @staticmethod
    def _items():
        employee_id = func.coalesce(AnomalyModel.employee_id, TimeEntryModel.employee_id)
        return (
            select(
                AnomalyModel.id,
                AnomalyModel.type,
                AnomalyModel.severity,
                AnomalyModel.status,
                AnomalyModel.detected_at,
                AnomalyModel.decided_at,
                AnomalyModel.decision_comment,
                employee_id.label("employee_id"),
                EmployeeModel.employee_number,
                _punched_user.first_name.label("employee_first_name"),
                _punched_user.last_name.label("employee_last_name"),
                _assistant_user.first_name.label("assisted_by_first_name"),
                _assistant_user.last_name.label("assisted_by_last_name"),
                TimeEntryModel.occured_at,
                TimeEntryModel.entry_type,
                TimeEntryModel.photo_key,
            )
            .select_from(AnomalyModel)
            .outerjoin(TimeEntryModel, TimeEntryModel.id == AnomalyModel.time_entry_id)
            .outerjoin(EmployeeModel, EmployeeModel.id == employee_id)
            .outerjoin(_punched_user, _punched_user.id == EmployeeModel.user_id)
            .outerjoin(_assistant_user, _assistant_user.id == AnomalyModel.assisted_by_user_id)
        )

    @staticmethod
    def _filtered(statement, status: AnomalyStatus | None, type: AnomalyType | None):
        if status is not None:
            statement = statement.where(AnomalyModel.status == AnomalyStatus(status).value)
        if type is not None:
            statement = statement.where(AnomalyModel.type == AnomalyType(type).value)
        return statement

    @staticmethod
    def _to_dto(row) -> AnomalyListItemDTO:
        entry_type = row.entry_type
        return AnomalyListItemDTO(
            id=row.id,
            type=AnomalyType(row.type),
            severity=Severity(row.severity),
            status=AnomalyStatus(row.status),
            detected_at=row.detected_at,
            employee_id=row.employee_id,
            employee_number=row.employee_number,
            employee_first_name=row.employee_first_name,
            employee_last_name=row.employee_last_name,
            assisted_by_first_name=row.assisted_by_first_name,
            assisted_by_last_name=row.assisted_by_last_name,
            occured_at=row.occured_at,
            entry_type=getattr(entry_type, "value", entry_type),
            photo_key=row.photo_key,
            decided_at=row.decided_at,
            decision_comment=row.decision_comment,
        )
