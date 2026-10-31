from dataclasses import dataclass
from datetime import datetime

from core.application import DTO
from identity.domain import Role
from identity.domain.entities import Employee


@dataclass(frozen=True)
class EmployeeDTO(DTO):
    id: str
    user_id: str
    employee_number: str
    role: Role
    is_active: bool
    phone: str | None = None
    company_directory_id: str | None = None
    # Onboarding only: the email already had an account, a new record was added to it.
    account_reused: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(cls, employee: Employee) -> "EmployeeDTO":
        return cls(
            id=employee.id.value,
            user_id=employee.user_id.value,
            role=employee.role,
            is_active=employee.is_active,
            phone=employee.phone,
            employee_number=employee.employee_number,
            company_directory_id=employee.company_directory_id.value if employee.company_directory_id else None,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
        )


@dataclass(frozen=True)
class EmployeesPageDTO(DTO):
    items: tuple[EmployeeDTO, ...]
    total: int