from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel


class OutboxStatus(StrEnum):
    """Lifecycle of an outbox row (storage concern, not a domain concept)."""

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxModel(BaseModel):
    """Outbox row: an integration event waiting to be relayed to a broker.

    Written in the same transaction as the aggregate's own write (see
    ``TransactionalOutbox``); drained by the ``OutboxRelay`` worker. Inherits
    ``id`` (row key) / ``created_at`` / ``updated_at`` / ``version_id`` from
    ``BaseModel``; ``event_id`` is the *event's* identity for idempotency.
    """

    __tablename__ = "outbox"

    event_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(
            OutboxStatus, values_callable=lambda enum_cls: [m.value for m in enum_cls]
        ),
        nullable=False,
        default=OutboxStatus.PENDING,
    )
    flush_counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
