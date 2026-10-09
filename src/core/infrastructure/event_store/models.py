from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel


class EventModel(BaseModel):
    """One stored domain event — the write side's source of truth.

    ``id`` is the event's own id. ``global_position`` orders every event of
    every stream (projections read in that order); ``stream_version`` orders
    the events of one aggregate and, being unique per stream, refuses a
    concurrent writer. Rows are never updated nor deleted.
    """

    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("stream_id", "stream_version", name="uq_events_stream_version"),
        Index("ix_events_stream_type", "stream_type"),
        Index("ix_events_payload", "payload", postgresql_using="gin", postgresql_ops={"payload": "jsonb_path_ops"}),
    )

    global_position: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True, nullable=False)
    stream_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stream_id: Mapped[str] = mapped_column(String(32), nullable=False)
    stream_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UniqueKeyModel(BaseModel):
    """A value reserved by one stream (an email, an employee number…).

    The event store cannot hold a unique index on "the current email of each
    user", so repositories reserve such values here, in the same transaction
    as the events: two concurrent writers cannot both take one.
    """

    __tablename__ = "unique_keys"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_unique_keys_scope_key"),)

    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_id: Mapped[str] = mapped_column(String(32), nullable=False)
