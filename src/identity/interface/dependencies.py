"""Interface-layer dependencies: the users container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db_session, get_password_hasher

from ..application.ports import PasswordHasher
from ..infrastructure import UsersContainer, build_users_container


def get_users(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> UsersContainer:
    """One users container per request, wired over the request-scoped session
    and the app-wide event bus."""
    return build_users_container(
        session=session,
        event_bus=request.app.state.container.event_bus,
        password_hasher=password_hasher,
    )
