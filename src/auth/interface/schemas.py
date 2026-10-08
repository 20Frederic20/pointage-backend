from typing import Annotated

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
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(alias="tokenType")
    expires_in: int = Field(alias="expiresIn")


class PrincipalResponse(_CamelSchema):
    user_id: str = Field(alias="userId")
    role: str
