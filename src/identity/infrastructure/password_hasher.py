"""Argon2id adapter for the :class:`PasswordHasher` port.

Argon2id at RFC 9106's low-memory profile (64 MiB, 3 passes, 4 lanes). The
parameters are pinned rather than left to the library's defaults, so a
dependency bump can never quietly change what a stored hash costs to verify.
Salting and parameter encoding are the library's job: ``hash`` returns a
self-describing string carrying its own salt and cost parameters, which is
why the port's ``verify`` needs nothing but the stored string.
"""

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type

from ..application.ports import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    """``PasswordHasher`` backed by Argon2id."""

    __slots__ = ("_argon2", "_dummy_hash")

    def __init__(self) -> None:
        self._argon2 = Argon2(
            time_cost=3,
            memory_cost=65536,  # KiB — 64 MiB
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        # Hashed once here, not per call: login verifies against this on the
        # unknown-email path, and hashing it on every request would make that
        # path measurably *slower* than the real one — the exact timing leak
        # it exists to close.
        self._dummy_hash = self._argon2.hash("dummy-password-for-timing")

    def hash(self, plain: str) -> str:
        return self._argon2.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return self._argon2.verify(hashed, plain)
        except (VerificationError, InvalidHashError):
            # Wrong password raises VerifyMismatchError (a VerificationError).
            # A corrupt or truncated stored hash raises InvalidHashError, which
            # derives from ValueError — *not* from VerificationError — so it has
            # to be named separately or it escapes as a 500 on a bad row.
            return False

    @property
    def dummy_hash(self) -> str:
        return self._dummy_hash