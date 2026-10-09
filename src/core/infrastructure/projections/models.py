from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel


class ProjectionCheckpointModel(BaseModel):
    """Read database: the last event position a projection runner applied.

    ``id`` is the runner's name. Updated in the same transaction as the
    read-model rows, so each event is projected exactly once.
    """

    __tablename__ = "projection_checkpoints"

    position: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class ProjectionFailureModel(BaseModel):
    """Read database: an event a projection could not apply, parked.

    ``id`` is the event's id. The runner records it and moves on, so one bad
    event never freezes every read model; the stream it belongs to is stale
    from that event on, until the cause is fixed and the read models are
    rebuilt (see ``sql/read_model.sql``).
    """

    __tablename__ = "projection_failures"

    runner: Mapped[str] = mapped_column(String(64), nullable=False)
    global_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stream_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stream_id: Mapped[str] = mapped_column(String(32), nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[str] = mapped_column(Text, nullable=False)
