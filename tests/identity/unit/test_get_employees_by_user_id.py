import asyncio

from identity.application.handlers import GetEmployeesByUserIdHandler
from identity.application.queries import GetEmployeesByUserIdQuery
from identity.application.services import EmployeeEnricher
from identity.domain import DirectoryId, EmployeeId, Role, UserId
from identity.domain.entities import Employee


def test_every_record_of_the_account_with_its_company_name(write_side):
    write_side.employees.add(
        Employee(EmployeeId("emp1"), user_id=UserId("usr1"), employee_number="EMP0000001", is_active=True,
                 role=Role.HR, company_directory_id=DirectoryId("dir1")),
        Employee(EmployeeId("emp2"), user_id=UserId("usr1"), employee_number="EMP0000002", is_active=False,
                 company_directory_id=DirectoryId("dir9")),
        Employee(EmployeeId("emp3"), user_id=UserId("usr2"), employee_number="EMP0000003", is_active=True),
    )
    handler = GetEmployeesByUserIdHandler(employee_repository=write_side.employees,
                                          enricher=EmployeeEnricher(directory_repository=write_side.directories))
    records = asyncio.run(handler.handle(GetEmployeesByUserIdQuery(user_id="usr1")))
    assert sorted((r.id, r.company_name, r.role, r.is_active) for r in records) == [
        ("emp1", "Société R", Role.HR, True), ("emp2", "Autre société", Role.EMPLOYEE, False)]
