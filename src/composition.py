from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.domain.events import BaseEvent
from core.domain.events.event_bus_schema import IEventBus
from core.infrastructure.outbox import OutboxRelay
from core.settings import AppSettings, DatabaseSettings


class AppContainer:
    """Composition root for app-wide singletons.

    Built by ``lifespan`` and shared with FastAPI dependencies via ``app.state``.
    Contexts expose their own containers (see ``inbox.InboxContainer``) that are
    built per request from the session factory here; the outbox relay is the
    one app-wide *worker* (see ``socialcrm.workers.outbox``).
    """

    def __init__(
        self,
        *,
        settings: AppSettings,
        database_settings: DatabaseSettings,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: IEventBus[BaseEvent],
        outbox_relay: OutboxRelay,
    ) -> None:
        self.settings = settings
        self.database_settings = database_settings
        self.engine = engine
        self.session_factory = session_factory
        self.event_bus = event_bus
        self.outbox_relay = outbox_relay
