import hmac
from datetime import datetime, timedelta

from core.domain.entity import AggregateRoot

from ..value_objects import LoginCodeId


class LoginCode(AggregateRoot[LoginCodeId]):
    """A one-time code emailed to log in without a password, stored hashed.

    Valid ``TTL``, usable once, and dead after ``MAX_ATTEMPTS`` wrong guesses.
    Only the latest code of a user counts: requesting a new one makes the
    previous ones useless.
    """

    TTL = timedelta(minutes=10)
    MAX_ATTEMPTS = 5

    __slots__ = ("_attempts", "_code_hash", "_consumed_at", "_expires_at", "_user_id")

    def __init__(
        self,
        code_id: LoginCodeId,
        *,
        user_id: str,
        code_hash: str,
        expires_at: datetime,
        attempts: int = 0,
        consumed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(code_id, created_at=created_at, updated_at=updated_at, version=version)
        self._user_id = user_id
        self._code_hash = code_hash
        self._expires_at = expires_at
        self._attempts = attempts
        self._consumed_at = consumed_at

    @classmethod
    def issue(cls, code_id: LoginCodeId, *, user_id: str, code_hash: str, now: datetime) -> "LoginCode":
        return cls(code_id, user_id=user_id, code_hash=code_hash, expires_at=now + cls.TTL, created_at=now)

    def is_usable(self, now: datetime) -> bool:
        return (
            self._consumed_at is None
            and now < self._expires_at
            and self._attempts < self.MAX_ATTEMPTS
        )

    def verify(self, code_hash: str, now: datetime) -> bool:
        """Consume the code on a match; count the attempt otherwise."""
        if not self.is_usable(now):
            return False
        if hmac.compare_digest(self._code_hash, code_hash):
            self._consumed_at = now
            self.touch()
            return True
        self._attempts += 1
        self.touch()
        return False

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def code_hash(self) -> str:
        return self._code_hash

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def consumed_at(self) -> datetime | None:
        return self._consumed_at
