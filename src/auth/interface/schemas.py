from typing import Annotated

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# An email or an employee number: the account is resolved by identity.
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]


# ---- requests --------------------------------------------------------------


class LoginRequest(_CamelSchema):
    identifier: Identifier
    password: str = Field(min_length=1)


class LoginCodeRequest(_CamelSchema):
    identifier: Identifier


class VerifyLoginCodeRequest(_CamelSchema):
    identifier: Identifier
    code: str = Field(pattern=r"^\d{6}$")


class RefreshTokenRequest(_CamelSchema):
    refresh_token: str = Field(alias="refreshToken", min_length=1)


# ---- responses -------------------------------------------------------------


class TokenPairResponse(_CamelSchema):
    status: Literal["authenticated"] = "authenticated"
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(alias="tokenType")
    expires_in: int = Field(alias="expiresIn")


class EmploymentResponse(_CamelSchema):
    employee_id: str = Field(alias="employeeId")
    company_name: str | None = Field(default=None, alias="companyName")
    role: str


class SelectionRequiredResponse(_CamelSchema):
    """Several active companies: ``POST /auth/select-employee`` with one of them."""

    status: Literal["selection_required"] = "selection_required"
    selection_token: str = Field(alias="selectionToken")
    employments: list[EmploymentResponse]


class SelectEmployeeRequest(_CamelSchema):
    selection_token: str = Field(alias="selectionToken", min_length=1)
    employee_id: str = Field(alias="employeeId", min_length=1)


class PrincipalResponse(_CamelSchema):
    employee_id: str | None = Field(default=None, alias="employeeId")
    user_id: str = Field(alias="userId")
    role: str
