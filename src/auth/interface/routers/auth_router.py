from fastapi import APIRouter, BackgroundTasks, Depends, status

from auth.application.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshSessionCommand,
    RequestLoginCodeCommand,
    VerifyLoginCodeCommand,
)
from auth.application.dtos import PrincipalDTO
from auth.application.ports import EmailSender
from auth.domain.errors import InvalidLoginCodeError, InvalidRefreshTokenError
from auth.infrastructure import AuthContainer
from auth.interface import (
    LoginCodeRequest,
    LoginRequest,
    PrincipalResponse,
    RefreshTokenRequest,
    TokenPairResponse,
    VerifyLoginCodeRequest,
    get_auth,
    get_current_principal,
    get_email_sender,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_response(dto) -> TokenPairResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return TokenPairResponse.model_validate(dto, from_attributes=True)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    auth: AuthContainer = Depends(get_auth),  # noqa: B008
) -> TokenPairResponse:
    """Email or employee number + password → access token (15 min) + refresh token.

    Only for accounts that have a password; the others log in by code.
    """
    dto = await auth.send(LoginCommand(identifier=payload.identifier, password=payload.password))
    return _to_response(dto)


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_login_code(
    payload: LoginCodeRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContainer = Depends(get_auth),  # noqa: B008
    email_sender: EmailSender = Depends(get_email_sender),  # noqa: B008
) -> None:
    """Email a 6-digit login code (valid 10 min) to a password-less account.

    ``identifier`` is an email or an employee number; the code goes to the
    account's email. Always 202, whatever the identifier, so the answer never tells whether the
    account exists. The email leaves after the response: the SMTP round
    trip never shows in the response time.
    """
    email = await auth.send(RequestLoginCodeCommand(identifier=payload.identifier))
    if email is not None:
        background_tasks.add_task(email_sender.send, email)


@router.post("/otp/verify", response_model=TokenPairResponse)
async def verify_login_code(
    payload: VerifyLoginCodeRequest,
    auth: AuthContainer = Depends(get_auth),  # noqa: B008
) -> TokenPairResponse:
    """Email or employee number + emailed code → the same token pair as a password login."""
    dto = await auth.send(VerifyLoginCodeCommand(identifier=payload.identifier, code=payload.code))
    if dto is None:
        # The handler already committed the failed attempt (see VerifyLoginCodeHandler).
        raise InvalidLoginCodeError("Invalid login code")
    return _to_response(dto)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshTokenRequest,
    auth: AuthContainer = Depends(get_auth),  # noqa: B008
) -> TokenPairResponse:
    """Rotate the refresh token. The old one stops working immediately, and
    the session gets another 36 h (never past 30 days after the login)."""
    dto = await auth.send(RefreshSessionCommand(refresh_token=payload.refresh_token))
    if dto is None:
        # The handler already committed the revocation (see RefreshSessionHandler).
        raise InvalidRefreshTokenError("Invalid refresh token")
    return _to_response(dto)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    auth: AuthContainer = Depends(get_auth),  # noqa: B008
) -> None:
    """Revoke the session. Always 204, even for an unknown token."""
    await auth.send(LogoutCommand(refresh_token=payload.refresh_token))


@router.get("/me", response_model=PrincipalResponse)
async def me(
    principal: PrincipalDTO = Depends(get_current_principal),  # noqa: B008
) -> PrincipalResponse:
    """Who the access token says the caller is."""
    return PrincipalResponse.model_validate(principal, from_attributes=True)
