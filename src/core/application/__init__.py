"""Shared application-layer foundation, built on python-cqrs.

- :class:`Command` / :class:`Query` — frozen-dataclass request markers.
- :class:`DTO` — frozen-dataclass response marker (query / command results).
- :class:`CommandHandler` / :class:`QueryHandler` — cqrs handler bases.
  ``CommandHandler`` is the write-use-case *template*: its ``handle`` owns
  the collect → persist → outbox-in-transaction → post-commit-dispatch
  ordering, so subclasses implement only ``_execute`` / ``_persist``;
  ``QueryHandler`` is the plain read base (no events, no transaction).
- :class:`ApplicationMediator` — per-request facade over cqrs' mediator.
- :class:`HandlerContainer` — resolves handlers from manual wiring.
- :class:`IUnitOfWork` — transaction boundary port (implemented by infrastructure).
- :class:`IEventOutbox` — transactional-outbox port (implemented by infrastructure).
"""

from .commands import Command
from .container import HandlerContainer
from .dtos import DTO
from .handlers import CommandHandler, QueryHandler, RequestHandlerBase
from .mediator import ApplicationMediator
from .outbox import IEventOutbox
from .queries import Query
from .unit_of_work import IUnitOfWork

__all__ = [
    "DTO",
    "ApplicationMediator",
    "Command",
    "CommandHandler",
    "HandlerContainer",
    "IEventOutbox",
    "IUnitOfWork",
    "Query",
    "QueryHandler",
    "RequestHandlerBase",
]
