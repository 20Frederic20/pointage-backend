"""Workspace routes. ``GET/PATCH /employees/me`` joins this routers together
with the auth context's guards in a later slice."""

from fastapi import APIRouter, Depends, status

from identity.application.commands.create_employee import CreateEmployeeCommand
from identity.infrastructure import UsersContainer
from identity.interface.schemas import CreateEmployeeRequest, EmployeeResponse

from ..dependencies import get_users

router = APIRouter(prefix="/employees", tags=["employees"])


def _employee_reponse(dto) -> EmployeeResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return EmployeeResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload: CreateEmployeeRequest,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    dto = await users.send(
        CreateEmployeeCommand(
            user_id=payload.user_id,
            directory_id=payload.directory_id,
            employee_number=payload.employee_number,
            is_active=payload.is_active,
            phone=payload.phone,
            role=payload.role,
            assignment_start_date=payload.assignment_start_date,
            site_id=payload.site_id,
        )
    )

    return _employee_reponse(dto)
