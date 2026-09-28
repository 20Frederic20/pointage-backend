from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """Opt-in soft delete for ORM models.

    Soft delete is a storage strategy, not a domain concern — models opt in by
    inheriting this mixin instead of every table getting a ``deleted_at``
    column. Filtering for ``deleted_at IS NULL`` in queries is the concrete
    repository's job.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
