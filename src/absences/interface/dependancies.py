"""Interface-layer dependencies: the absences container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_read_session, get_write_session

from ..infrastructure import AbsencesContainer, build_absences_container


def get_absences(
    request: Request,
    write_session: AsyncSession = Depends(get_write_session),
    read_session: AsyncSession = Depends(get_read_session),
) -> AbsencesContainer:
    """One absences container per request, wired over the request-scoped
    sessions (write: event store, read: read models) and the app-wide event bus."""
    return build_absences_container(
        write_session=write_session,
        read_session=read_session,
        event_bus=request.app.state.container.event_bus,
    )
