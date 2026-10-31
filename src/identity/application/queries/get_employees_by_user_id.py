from dataclasses import dataclass

from core.application import Query

from ..dtos import EmployeeDTO


@dataclass(frozen=True)
class GetEmployeesByUserIdQuery(Query):
    """Every employee record of an account, one per company (with the company name)."""

    user_id: str

    Result = tuple[EmployeeDTO, ...]
