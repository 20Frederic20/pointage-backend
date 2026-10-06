import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auth.infrastructure import JwtTokenIssuer, SmtpEmailSender
from composition import AppContainer
from core.infrastructure.database import build_engine, build_session_factory
from core.infrastructure.events import InProcessEventBus
from workers.outbox import build_outbox_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: build the composition root. Shutdown: dispose the engine.

    ``build_engine`` is lazy — no connection is made here, so the app boots
    even if the database is temporarily unreachable (the connection happens on
    the first query). The outbox relay follows the same rule: it starts
    immediately and retries each poll until the database answers.
    """
    settings = app.state.settings
    database_settings = app.state.database_settings

    engine = build_engine(database_settings)
    session_factory = build_session_factory(engine)
    # Cross-context subscriptions (contacts, automation, realtime) register
    # on this bus during startup.
    event_bus = InProcessEventBus()

    outbox_relay = build_outbox_worker(session_factory=session_factory)
    relay_task = asyncio.create_task(outbox_relay.run(), name="outbox-relay")

    app.state.container = AppContainer(
        settings=settings,
        database_settings=database_settings,
        engine=engine,
        session_factory=session_factory,
        event_bus=event_bus,
        outbox_relay=outbox_relay,
        token_issuer=JwtTokenIssuer(app.state.auth_settings),
        email_sender=SmtpEmailSender(app.state.mail_settings),
    )
    try:
        yield
    finally:
        outbox_relay.stop()
        await relay_task
        await engine.dispose()
