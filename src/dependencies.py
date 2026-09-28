"""App-wide FastAPI dependencies — the request-scope entry points.

Built on the composition root ``lifespan`` hangs off ``app.state.container``
(see :mod:`composition`). Bounded contexts own their own container per
request (e.g. ``identity.interface.dependencies.get_users``) and build it from
the session and adapters these dependencies hand out.
"""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio.session import AsyncSession

from identity.application.ports import PasswordHasher
from identity.infrastructure.password_hasher import Argon2PasswordHasher


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One database session per request, closed when the request ends.

    Nothing is committed here: the session is handed to a context's unit of
    work, which owns the transaction boundary and commits on clean exit. The
    ``async with`` closes the session either way, so a handler that raises
    cannot leak a connection back to the pool.
    """
    session_factory = request.app.state.container.session_factory
    async with session_factory() as session:
        yield session


# Module-level instance: Argon2PasswordHasher hashes its dummy value in
# __init__, so building one per request would pay a full 64 MiB argon2 hash
# every time. Stateless and thread-safe, so sharing it is safe.
_PASSWORD_HASHER = Argon2PasswordHasher()


def get_password_hasher() -> PasswordHasher:
    """The app-wide password hasher."""
    return _PASSWORD_HASHER
