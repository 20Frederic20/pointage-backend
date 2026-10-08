from abc import abstractmethod

from core.domain.repositories import IRepository
from identity.domain import EmployeeId, UserId
from identity.domain.entities import Employee


class IEmployeeRepository(IRepository[Employee, EmployeeId]):

    @abstractmethod
    async def exists_by_employee_number(self, employee_number: str) -> bool:
        ...

    @abstractmethod
    async def find_by_employee_number(self, employee_number: str) -> Employee | None:
        ...

    @abstractmethod
    async def find_by_user_id(self, user_id: UserId) -> Employee | None:
        """The employee record of an account, the active one first."""
        ...