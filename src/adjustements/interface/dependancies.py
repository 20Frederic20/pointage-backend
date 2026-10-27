"""Interface-layer dependencies: the adjustements container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_read_session, get_write_session

from ..infrastructure.container import AdjustementsContainer, build_adjustements_container


def get_anomalies(
    request: Request,
    write_session: AsyncSession = Depends(get_write_session),  # noqa: B008
    read_session: AsyncSession = Depends(get_read_session),  # noqa: B008
) -> AdjustementsContainer:
    """One adjustements container per request, wired over the request-scoped
    sessions (write: event store, read: read models), the app-wide event bus
    and the app-wide selfie storage."""
    return build_adjustements_container(
        write_session=write_session,
        read_session=read_session,
        event_bus=request.app.state.container.event_bus,
        photo_storage=request.app.state.container.photo_storage,
    )
