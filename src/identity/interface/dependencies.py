"""Interface-layer dependencies: the users container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_password_hasher, get_read_session, get_write_session

from ..application.ports import PasswordHasher
from ..infrastructure import UsersContainer, build_users_container


def get_users(
    request: Request,
    write_session: AsyncSession = Depends(get_write_session),
    read_session: AsyncSession = Depends(get_read_session),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> UsersContainer:
    """One users container per request, wired over the request-scoped
    sessions (write: event store, read: read models) and the app-wide event bus."""
    return build_users_container(
        write_session=write_session,
        read_session=read_session,
        event_bus=request.app.state.container.event_bus,
        password_hasher=password_hasher,
    )
