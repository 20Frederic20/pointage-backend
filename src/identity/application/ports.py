"""Ports the users application layer owns.

``PasswordHasher`` is the single password primitive: registration hashes,
login verifies. The concrete implementation (argon2) lives in the auth
context's infrastructure — the domain and application layers only ever
see this port.
"""

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Password hashing / verification contract."""

    @abstractmethod
    def hash(self, plain: str) -> str:
        """Hash a plain-text password."""
        ...

    @abstractmethod
    def verify(self, plain: str, hashed: str) -> bool:
        """Verify a plain-text password against a stored hash.

        Always returns a bool — an invalid stored hash is a ``False`` verdict,
        never an exception.
        """
        ...

    @property
    @abstractmethod
    def dummy_hash(self) -> str:
        """A precomputed hash of a throwaway value.

        Login runs exactly one ``verify`` on every path — including the
        unknown-email path — so response timing cannot reveal whether an
        account exists.
        """
        ...