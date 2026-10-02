"""Interface-layer dependencies: the punches container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db_session, get_password_hasher

from ..infrastructure import PunchesContainer, build_punches_container


def get_punches(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PunchesContainer:
    """One punches container per request, wired over the request-scoped session
    and the app-wide event bus."""
    return build_punches_container(
        session=session,
        event_bus=request.app.state.container.event_bus,
    )
