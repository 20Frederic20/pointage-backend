"""Interface-layer dependencies: the auth container per request, and the
guards every other context's routers use.

Guards only answer "who is calling?" and "may this role call this route?".
Business authorization (a manager only validates their own directory, an
employee only punches for themselves) stays in the handlers: routers pass
``principal.user_id`` into the command.
"""

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_password_hasher, get_write_session
from identity.application.ports import PasswordHasher

from ..application.dtos import PrincipalDTO
from ..application.ports import EmailSender, TokenIssuer
from ..domain.errors import AccessDeniedError, InvalidAccessTokenError
from ..infrastructure import AuthContainer, IdentityUserAccounts, build_auth_container

# auto_error=False: a missing header goes through our DomainError handler
# (same JSON error shape as every other error) instead of FastAPI's 403.
_bearer = HTTPBearer(auto_error=False)


def get_token_issuer(request: Request) -> TokenIssuer:
    """The app-wide token issuer, built once in ``lifespan``."""
    return request.app.state.container.token_issuer


def get_email_sender(request: Request) -> EmailSender:
    """The app-wide email sender, built once in ``lifespan``."""
    return request.app.state.container.email_sender


def get_auth(
    request: Request,
    session: AsyncSession = Depends(get_write_session),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    token_issuer: TokenIssuer = Depends(get_token_issuer),
) -> AuthContainer:
    """One auth container per request, wired over the request-scoped write session
    (auth's own tables live in the write database)."""
    app_container = request.app.state.container
    return build_auth_container(
        session=session,
        event_bus=app_container.event_bus,
        user_accounts=IdentityUserAccounts(
            session_factory=app_container.session_factory,
            read_session_factory=app_container.read_session_factory,
            event_bus=app_container.event_bus,
            password_hasher=password_hasher,
        ),
        password_hasher=password_hasher,
        token_issuer=token_issuer,
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token_issuer: TokenIssuer = Depends(get_token_issuer),
) -> PrincipalDTO:
    """The authenticated caller, or ``401 INVALID_ACCESS_TOKEN``.

    Stateless: signature and expiry only, no database query.
    """
    if credentials is None:
        raise InvalidAccessTokenError("Missing bearer access token")
    return token_issuer.decode_access_token(credentials.credentials)


def get_optional_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token_issuer: TokenIssuer = Depends(get_token_issuer),
) -> PrincipalDTO | None:
    """Like :func:`get_current_principal`, but ``None`` without a header.

    A header carrying a bad token is still a 401, never an anonymous call.
    """
    if credentials is None:
        return None
    return token_issuer.decode_access_token(credentials.credentials)


def require_role(*roles: str) -> Callable[..., PrincipalDTO]:
    """Allow only the listed roles: ``Depends(require_role(Role.HR, Role.ADMIN))``.

    An explicit list, not a rank: HR, PAYROLL and MANAGER are different jobs,
    not levels of one ladder.
    """
    allowed = frozenset(roles)

    def _guard(principal: PrincipalDTO = Depends(get_current_principal)) -> PrincipalDTO:
        if principal.role not in allowed:
            raise AccessDeniedError(
                f"Role {principal.role} is not allowed here", context=principal.user_id
            )
        return principal

    return _guard
