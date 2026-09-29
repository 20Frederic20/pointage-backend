from abc import abstractmethod

from core.domain.repositories import IRepository
from identity.domain import EmployeeId
from identity.domain.entities import Employee


class IEmployeeRepository(IRepository[Employee, EmployeeId]):

    @abstractmethod
    async def exists_by_employee_number(self, employee_nnumber):
        ...