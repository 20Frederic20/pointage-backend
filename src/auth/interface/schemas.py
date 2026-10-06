from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# ---- requests --------------------------------------------------------------


class LoginRequest(_CamelSchema):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginCodeRequest(_CamelSchema):
    email: EmailStr


class VerifyLoginCodeRequest(_CamelSchema):
    email: EmailStr
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
