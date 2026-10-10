from abc import abstractmethod

from core.domain.repositories import IRepository
from core.domain.repositories.base_read_repository import IReadRepository
from core.domain.repositories.base_write_repository import IWriteRepository
from core.domain.specifications import Specification
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

    @abstractmethod
    async def find(
        self,
        spec: Specification[Employee],
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Employee]:
        ...

    @abstractmethod
    async def count(self, spec: Specification[Employee]) -> int:
        """Employees matching ``spec`` — the ``total`` of a paged listing, before
        limit/offset are applied."""
        ...


class IEmployeeWriteRepository(IWriteRepository[Employee, EmployeeId]):

    @abstractmethod
    async def exists_by_employee_number(self, employee_number: str) -> bool:
        ...

    @abstractmethod
    async def find_by_user_id(self, user_id: UserId) -> Employee | None:
        """The employee record of an account, the active one first."""
        ...


class IemployeeReadRepository(IReadRepository[Employee, EmployeeId]):

    @abstractmethod
    async def find_by_employee_number(self, employee_number: str) -> Employee | None:
        ...