"""Interface-layer dependencies: the absences container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db_session

from ..infrastructure import AbsencesContainer, build_absences_container


def get_absences(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AbsencesContainer:
    """One absences container per request, wired over the request-scoped
    session and the app-wide event bus."""
    return build_absences_container(
        session=session,
        event_bus=request.app.state.container.event_bus,
    )
