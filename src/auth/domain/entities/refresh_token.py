from datetime import datetime, timedelta

from core.domain.entity import AggregateRoot

from ..errors import RefreshTokenNotUsableError
from ..value_objects import RefreshTokenId, TokenFamilyId


class RefreshToken(AggregateRoot[RefreshTokenId]):
    """A refresh token, stored only as a hash.

    Sessions slide: each use rotates the token, and the successor expires
    ``idle_ttl`` after that use — so a session dies after ``idle_ttl``
    without activity (evening → next morning survives, Friday → Monday does
    not). ``session_expires_at`` caps the whole family: no rotation reaches
    past it, however active the user is.

    Presenting a revoked token again means it was copied, so the caller
    revokes the whole family (see ``RefreshSessionHandler``).
    """

    __slots__ = (
        "_employee_id",
        "_expires_at",
        "_family_id",
        "_revoked_at",
        "_session_expires_at",
        "_token_hash",
        "_user_id",
    )

    def __init__(
        self,
        token_id: RefreshTokenId,
        *,
        user_id: str,
        token_hash: str,
        family_id: TokenFamilyId,
        expires_at: datetime,
        session_expires_at: datetime,
        revoked_at: datetime | None = None,
        employee_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(token_id, created_at=created_at, updated_at=updated_at, version=version)
        self._user_id = user_id
        self._token_hash = token_hash
        self._family_id = family_id
        self._expires_at = expires_at
        self._session_expires_at = session_expires_at
        self._revoked_at = revoked_at
        # The employee record the session works with (``None``: none, or a
        # session opened before records were bound).
        self._employee_id = employee_id

    @classmethod
    def start_session(
        cls,
        token_id: RefreshTokenId,
        *,
        user_id: str,
        token_hash: str,
        now: datetime,
        idle_ttl: timedelta,
        max_lifetime: timedelta,
        employee_id: str | None = None,
    ) -> "RefreshToken":
        """The first token of a new session (a login)."""
        session_expires_at = now + max_lifetime
        return cls(
            token_id,
            user_id=user_id,
            token_hash=token_hash,
            family_id=TokenFamilyId.generate(),
            expires_at=min(now + idle_ttl, session_expires_at),
            session_expires_at=session_expires_at,
            employee_id=employee_id,
        )

    def is_revoked(self) -> bool:
        return self._revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return now >= self._expires_at

    def is_usable(self, now: datetime) -> bool:
        return not self.is_revoked() and not self.is_expired(now)

    def revoke(self, now: datetime) -> None:
        """Idempotent: an already revoked token keeps its first revocation date."""
        if self.is_revoked():
            return
        self._revoked_at = now
        self.touch()

    def rotate(
        self,
        *,
        successor_id: RefreshTokenId,
        successor_hash: str,
        now: datetime,
        idle_ttl: timedelta,
        employee_id: str | None = None,
    ) -> "RefreshToken":
        """Revoke this token and return its successor, ``idle_ttl`` from now.

        The successor keeps the session's employee record, or binds ``employee_id``.
        """
        if not self.is_usable(now):
            raise RefreshTokenNotUsableError(
                "Refresh token is revoked or expired", context=self.id.value
            )
        self.revoke(now)
        return RefreshToken(
            successor_id,
            user_id=self._user_id,
            token_hash=successor_hash,
            family_id=self._family_id,
            expires_at=min(now + idle_ttl, self._session_expires_at),
            session_expires_at=self._session_expires_at,
            employee_id=employee_id or self._employee_id,
        )

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def employee_id(self) -> str | None:
        return self._employee_id

    @property
    def token_hash(self) -> str:
        return self._token_hash

    @property
    def family_id(self) -> TokenFamilyId:
        return self._family_id

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def session_expires_at(self) -> datetime:
        return self._session_expires_at

    @property
    def revoked_at(self) -> datetime | None:
        return self._revoked_at
