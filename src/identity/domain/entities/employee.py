from datetime import datetime
from typing import Self

from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId, Role, UserId
from identity.domain.events.employee_events import EmployeeCreated, EmployeeImported, EmployeeUpdated


class Employee(AggregateRoot[EmployeeId]):

    __slots__ = ("_employee_number", "_is_active", "_phone", "_role", "_user_id", "_employee_id",)

    def __init__ (
        self,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
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
        self._user_id = user_id
        self._employee_id  = employee_id
        self._employee_number = employee_number
        self._role = role
        self._is_active =  is_active
        self._phone = phone

    @classmethod
    def create(
        cls,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
        employee_number: str,
        is_active: bool,
        phone: str | None = None,
        role: Role = Role.EMPLOYEE,
    ) -> Self:
        """
        Founding signup: the first employee of a brand-new workspace,.
        """
        employee = cls.rehydrate(employee_id, [])
        employee._raise(
            EmployeeCreated(
                employee_id,
                user_id=user_id,
                employee_number=employee_number,
                is_active=is_active,
                phone=phone,
                role=role,
            )
        )
        return employee

    def update (
        self,
        *,
        employee_number: str | None,
        is_active: bool | None,
        phone: str | None,
    ) -> None:
        """Apply the fields sent (``None`` = untouched); nothing changed: nothing recorded."""
        event = EmployeeUpdated(
            self.id,
            employee_number=employee_number if employee_number is not None else self._employee_number,
            is_active=is_active if is_active is not None else self._is_active,
            phone=phone if phone is not None else self._phone,
        )
        if (event.employee_number, event.is_active, event.phone) == (self._employee_number, self._is_active, self._phone):
            return
        self._raise(event)

    def _apply(self, event) -> None:
        match event:
            case EmployeeCreated() | EmployeeImported():
                self._employee_id = event.employee_id
                self._user_id = event.user_id
                self._employee_number = event.employee_number
                self._is_active = event.is_active
                self._phone = event.phone
                self._role = event.role
                if isinstance(event, EmployeeImported):
                    self._created_at = event.created_at
            case EmployeeUpdated():
                self._employee_number = event.employee_number
                self._is_active = event.is_active
                self._phone = event.phone
            case _:
                super()._apply(event)

    @property
    def user_id(self) -> UserId:
        return self._user_id

    @property
    def employee_number(self) -> str:
        return self._employee_number

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def role(self) -> Role:
        return self._role

    @property
    def phone(self) -> str | None:
        return self._phone