"""Workspace routes. ``GET/PATCH /employees/me`` joins this routers together
with the auth context's guards in a later slice."""

from fastapi import APIRouter, Depends, HTTPException, status

from auth.interface import require_role
from identity.application import (
    GetEmployeeByIdQuery,
    GetEmployeesQuery,
    OnboardEmployeeCommand,
)
from identity.application.commands.create_employee import CreateEmployeeCommand
from identity.domain import Role
from identity.infrastructure import UsersContainer
from identity.interface import UpdateEmployeeRequest
from identity.interface.schemas import (
    CreateEmployeeRequest,
    EmployeeListResponse,
    EmployeeResponse,
    OnboardEmployeeRequest,
    RoleSchema,
)

from ..dependencies import get_users

router = APIRouter(prefix="/employees", tags=["employees"])


def _employee_reponse(dto) -> EmployeeResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return EmployeeResponse.model_validate(dto, from_attributes=True)


def _employee_list_response(page) -> EmployeeListResponse:
    """Page DTO (items + total) → wire schema; items are converted one by one."""
    return EmployeeListResponse.model_validate(page, from_attributes=True)


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


@router.post(
    "/onboard",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def onboard(
    payload: OnboardEmployeeRequest,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    """Create the account and the employee together (ADMIN only): both are
    saved, or neither — a taken email or number leaves no account behind."""
    dto = await users.send(
        OnboardEmployeeCommand(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
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


@router.patch(
    "/{id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK
)
async def update(
    payload: UpdateEmployeeRequest,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    ...
    # dto = await users.send(
    #     UpdateEmployeeCommand(
    #         user_id=payload.user_id,
    #         directory_id=payload.directory_id,
    #         employee_number=payload.employee_number,
    #         is_active=payload.is_active,
    #         phone=payload.phone,
    #         role=payload.role,
    #         assignment_start_date=payload.assignment_start_date,
    #         site_id=payload.site_id,
    #     )
    # )

    # return _employee_reponse(dto)


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    employee_number: str | None = None,
    role: RoleSchema | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeListResponse:
    page = await users.send(
        GetEmployeesQuery(
            employee_number=employee_number,
            # Wire enum → domain enum: the domain specs compare by identity.
            role=Role(role) if role is not None else None,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
    )
    return _employee_list_response(page)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    dto = await users.send(GetEmployeeByIdQuery(employee_id=employee_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return _employee_reponse(dto)
