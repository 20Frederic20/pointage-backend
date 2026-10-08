from core.domain.errors import DomainError, Severity


class InvalidCredentialsError(DomainError):
    """Raised on a failed login.

    One error for an unknown identifier, a wrong password and an inactive account,
    so the response never tells which accounts exist.
    """

    code = "INVALID_CREDENTIALS"
    http_status = 401
    severity = Severity.WARNING


class InvalidRefreshTokenError(DomainError):
    """Raised when a refresh token is unknown, expired or revoked."""

    code = "INVALID_REFRESH_TOKEN"
    http_status = 401
    severity = Severity.WARNING


class InvalidLoginCodeError(DomainError):
    """Raised when an emailed login code is wrong, expired, used or exhausted.

    One error for every case, an unknown identifier included.
    """

    code = "INVALID_LOGIN_CODE"
    http_status = 401
    severity = Severity.WARNING


class InvalidAccessTokenError(DomainError):
    """Raised when the bearer access token is missing, malformed or expired."""

    code = "INVALID_ACCESS_TOKEN"
    http_status = 401
    severity = Severity.WARNING


class AccessDeniedError(DomainError):
    """Raised when an authenticated caller's role is not allowed on a route."""

    code = "ACCESS_DENIED"
    http_status = 403
    severity = Severity.WARNING


class RefreshTokenNotUsableError(DomainError):
    """Raised when rotating a refresh token that is revoked or expired."""

    code = "REFRESH_TOKEN_NOT_USABLE"
    http_status = 401
    severity = Severity.WARNING
