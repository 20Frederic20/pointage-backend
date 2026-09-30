from datetime import UTC, datetime
from typing import Self

from core.domain.entity import AggregateRoot
from identity.domain import DirectoryId, EmployeeId, Role, UserId
from identity.domain.events import EmployeeCreated


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Employee(AggregateRoot[EmployeeId]):

    def __init__ (
        self,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
        directory_id: DirectoryId,
        employee_number: str,
        is_active: bool,
        phone: str | None = None,
        role: Role = Role.EMPLOYEE,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    )-> None:
        super().__init__(
            employee_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._user_id = user_id,
        self._employee_id  = employee_id,
        self._employee_number = employee_number,
        self._directory_id = directory_id,
        self._role = role
        self._is_active =  is_active
        self._phone = phone

    @classmethod
    def create(
        cls,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
        directory_id: DirectoryId,
        employee_number: str,
        is_active: bool,
        phone: str | None = None,
        role: Role = Role.EMPLOYEE,
    ) -> Self:
        """
        Founding signup: the first employee of a brand-new workspace,.
        """
        employee = cls(
            employee_id,
            user_id=user_id,
            directory_id=directory_id,
            role=role,
            employee_number=employee_number,
            is_active=is_active,
            phone=phone
        )
        employee.record_event(EmployeeCreated(employee_id))
        return employee

    def update (
        self,
        *
        employee_number: str | None,
        is_active: bool | None,
        phone: str | None,
    ) -> None:

        if employee_number is not None:
            self._employee_number = employee_number
        if is_active is not None:
            self._is_active = is_active
        if phone is not None:
            self._phone = phone
        self.touch()

    def record_activity(self) -> None:
        self._last_active_at = _utcnow()
        self.touch()

    @property
    def user_id(self) -> UserId:
        return self._user_id

    @property
    def directory_id(self) -> DirectoryId:
        return self._directory_id

    @property
    def employee_number(self) -> str:
        return self._employee_number

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def role(self) -> str:
        return self._role

    @property
    def phone(self) -> str | None:
        return self._phone