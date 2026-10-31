"""PyJWT adapter for the :class:`TokenIssuer` port.

Access tokens are HS256 JWTs signed with ``AuthSettings.jwt_secret``; decoding
pins the algorithm list, so a token signed with ``alg: none`` or another
algorithm is rejected. Refresh tokens are 384 random bits; only their
SHA-256 is stored (a fast hash is enough for a high-entropy secret). Login
codes have only 6 digits, so they are hashed with HMAC keyed by the JWT
secret: a leaked table cannot be brute-forced without the secret.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from core.settings import AuthSettings

from ..application.dtos import PrincipalDTO
from ..application.ports import TokenIssuer
from ..domain.errors import InvalidAccessTokenError

_ACCESS_TOKEN_TYPE = "access"
_SELECTION_TOKEN_TYPE = "employee_selection"


class JwtTokenIssuer(TokenIssuer):
    __slots__ = ("_settings",)

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    @property
    def access_token_ttl_seconds(self) -> int:
        return self._settings.access_token_ttl_seconds

    @property
    def refresh_token_idle_ttl(self) -> timedelta:
        return timedelta(hours=self._settings.refresh_token_idle_hours)

    @property
    def session_max_lifetime(self) -> timedelta:
        return timedelta(days=self._settings.session_max_days)

    def issue_access_token(self, *, user_id: str, role: str, employee_id: str | None = None) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": user_id,
            "role": role,
            "employee_id": employee_id,
            "typ": _ACCESS_TOKEN_TYPE,
            "iss": self._settings.jwt_issuer,
            "iat": now,
            "exp": now + timedelta(seconds=self._settings.access_token_ttl_seconds),
        }
        return jwt.encode(claims, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> PrincipalDTO:
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
                issuer=self._settings.jwt_issuer,
                options={"require": ["exp", "iat", "iss", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidAccessTokenError("Invalid or expired access token") from exc
        if claims.get("typ") != _ACCESS_TOKEN_TYPE or not isinstance(claims.get("role"), str):
            raise InvalidAccessTokenError("Invalid or expired access token")
        employee_id = claims.get("employee_id")  # absent from tokens issued before it existed
        return PrincipalDTO(
            user_id=claims["sub"],
            role=claims["role"],
            employee_id=employee_id if isinstance(employee_id, str) else None,
        )

    def issue_selection_token(self, *, user_id: str) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": user_id,
            "typ": _SELECTION_TOKEN_TYPE,
            "iss": self._settings.jwt_issuer,
            "iat": now,
            "exp": now + timedelta(seconds=self._settings.selection_token_ttl_seconds),
        }
        return jwt.encode(claims, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm)

    def decode_selection_token(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
                issuer=self._settings.jwt_issuer,
                options={"require": ["exp", "iat", "iss", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidAccessTokenError("Invalid or expired selection token") from exc
        if claims.get("typ") != _SELECTION_TOKEN_TYPE:
            raise InvalidAccessTokenError("Invalid or expired selection token")
        return claims["sub"]

    def new_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def hash_refresh_token(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def new_login_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def hash_login_code(self, *, user_id: str, code: str) -> str:
        message = f"{user_id}:{code.strip()}".encode()
        return hmac.new(self._settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()
