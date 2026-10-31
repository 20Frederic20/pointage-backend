from datetime import datetime
from typing import Self

from core.domain.entity import AggregateRoot
from identity.domain import DirectoryId, EmployeeId, Role, UserId
from identity.domain.errors import EmployeeAlreadyActiveError, EmployeeAlreadyInactiveError
from identity.domain.events.employee_events import (
    EmployeeActivated,
    EmployeeCompanySet,
    EmployeeCreated,
    EmployeeDeactivated,
    EmployeeImported,
    EmployeeRoleChanged,
    EmployeeUpdated,
)


class Employee(AggregateRoot[EmployeeId]):

    __slots__ = ("_company_directory_id", "_employee_number", "_is_active", "_phone", "_role", "_user_id", "_employee_id",)

    def __init__ (
        self,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
        employee_number: str,
        is_active: bool,
        phone: str | None = None,
        role: Role = Role.EMPLOYEE,
        company_directory_id: DirectoryId | None = None,
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
        self._company_directory_id = company_directory_id

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
        company_directory_id: DirectoryId | None = None,
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
                company_directory_id=company_directory_id,
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

    def change_phone(self, phone: str | None) -> None:
        """New phone (``None`` = untouched)."""
        self.update(employee_number=None, is_active=None, phone=phone)

    def change_role(self, role: Role) -> None:
        """The role in this company; same role: nothing recorded."""
        if role == self._role:
            return
        self._raise(EmployeeRoleChanged(self.id, role=role))

    def deactivate(self) -> None:
        """Leave or departure: the record can no longer punch."""
        if not self._is_active:
            raise EmployeeAlreadyInactiveError(f"Employee {self.id.value} is already inactive", context=self.id.value)
        self._raise(EmployeeDeactivated(self.id))

    def activate(self) -> None:
        if self._is_active:
            raise EmployeeAlreadyActiveError(f"Employee {self.id.value} is already active", context=self.id.value)
        self._raise(EmployeeActivated(self.id))

    def set_company(self, directory_id: DirectoryId) -> None:
        """Backfill only: the company (root directory) of a record created before it was stored."""
        self._raise(EmployeeCompanySet(self.id, company_directory_id=directory_id))

    def _apply(self, event) -> None:
        match event:
            case EmployeeCreated() | EmployeeImported():
                self._employee_id = event.employee_id
                self._user_id = event.user_id
                self._employee_number = event.employee_number
                self._is_active = event.is_active
                self._phone = event.phone
                self._role = event.role
                self._company_directory_id = event.company_directory_id
                if isinstance(event, EmployeeImported):
                    self._created_at = event.created_at
            case EmployeeUpdated():
                self._employee_number = event.employee_number
                self._is_active = event.is_active
                self._phone = event.phone
            case EmployeeRoleChanged():
                self._role = event.role
            case EmployeeDeactivated():
                self._is_active = False
            case EmployeeActivated():
                self._is_active = True
            case EmployeeCompanySet():
                self._company_directory_id = event.company_directory_id
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

    @property
    def company_directory_id(self) -> DirectoryId | None:
        return self._company_directory_id
