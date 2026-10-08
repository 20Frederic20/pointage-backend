"""Ports the auth application layer owns.

``TokenIssuer`` hides the token and code formats (JWT today);
``UserAccounts`` is the only way auth reaches the accounts, which identity
owns — auth never touches the ``users`` table or ``UserRepository``;
``EmailSender`` delivers the login codes.
"""

from abc import ABC, abstractmethod
from datetime import timedelta

from .dtos import AccountCredentialsDTO, AccountDTO, OutgoingEmailDTO, PrincipalDTO


class TokenIssuer(ABC):
    """Access tokens (signed, stateless) and refresh tokens (opaque, random)."""

    @property
    @abstractmethod
    def access_token_ttl_seconds(self) -> int:
        ...

    @property
    @abstractmethod
    def refresh_token_idle_ttl(self) -> timedelta:
        """How long a session survives without any refresh."""
        ...

    @property
    @abstractmethod
    def session_max_lifetime(self) -> timedelta:
        """How long a session survives at most, however active."""
        ...

    @abstractmethod
    def issue_access_token(self, *, user_id: str, role: str) -> str:
        ...

    @abstractmethod
    def decode_access_token(self, token: str) -> PrincipalDTO:
        """Verify signature, issuer and expiry.

        Raises ``InvalidAccessTokenError`` on any failure.
        """
        ...

    @abstractmethod
    def new_refresh_token(self) -> str:
        """A fresh random refresh token (the raw value handed to the client)."""
        ...

    @abstractmethod
    def hash_refresh_token(self, raw: str) -> str:
        """The deterministic hash stored and looked up instead of the raw value."""
        ...

    @abstractmethod
    def new_login_code(self) -> str:
        """A fresh 6-digit code to email."""
        ...

    @abstractmethod
    def hash_login_code(self, *, user_id: str, code: str) -> str:
        """Keyed hash of a code, bound to its user.

        A 6-digit code is guessable offline from a plain hash; keying it with
        a server secret keeps a leaked table useless.
        """
        ...


class UserAccounts(ABC):
    """The identity accounts, seen from auth."""

    @abstractmethod
    async def find_credentials(self, identifier: str) -> AccountCredentialsDTO | None:
        """The account behind an email or an employee number, or ``None``."""
        ...

    @abstractmethod
    async def get_account(self, user_id: str) -> AccountDTO | None:
        ...

    @abstractmethod
    async def record_activity(self, user_id: str) -> None:
        """Best effort: a failure here must never fail a login or a refresh."""
        ...


class EmailSender(ABC):

    @abstractmethod
    async def send(self, email: OutgoingEmailDTO) -> None:
        """Deliver ``email``. Best effort: failures are logged, never raised."""
        ...
