from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession

from auth.application.ports import EmailSender, TokenIssuer
from core.domain.events import BaseEvent
from core.domain.events.event_bus_schema import IEventBus
from core.infrastructure.outbox import OutboxRelay
from core.infrastructure.projections import ProjectionRunner
from core.settings import AppSettings, DatabaseSettings


class AppContainer:
    """Composition root for app-wide singletons.

    Built by ``lifespan`` and shared with FastAPI dependencies via ``app.state``.
    Contexts expose their own containers (see ``inbox.InboxContainer``) that are
    built per request from the session factories here: ``session_factory``
    is the write database (event store), ``read_session_factory`` the read
    database (read models). The two app-wide *workers* are the outbox relay
    (see ``workers.outbox``) and the projection runner that feeds the read
    database from the event store (see ``workers.projections``).
    """

    def __init__(
        self,
        *,
        settings: AppSettings,
        database_settings: DatabaseSettings,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        read_engine: AsyncEngine,
        read_session_factory: async_sessionmaker[AsyncSession],
        event_bus: IEventBus[BaseEvent],
        outbox_relay: OutboxRelay,
        projection_runner: ProjectionRunner,
        token_issuer: TokenIssuer,
        email_sender: EmailSender,
    ) -> None:
        self.settings = settings
        self.database_settings = database_settings
        self.engine = engine
        self.session_factory = session_factory
        self.read_engine = read_engine
        self.read_session_factory = read_session_factory
        self.event_bus = event_bus
        self.outbox_relay = outbox_relay
        self.projection_runner = projection_runner
        self.token_issuer = token_issuer
        self.email_sender = email_sender
