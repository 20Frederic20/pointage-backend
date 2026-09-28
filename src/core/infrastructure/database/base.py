from datetime import datetime

from cuid2 import cuid_wrapper
from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import DateTime, String

cuid_generator = cuid_wrapper()


class BaseModel(DeclarativeBase):
    # Stable constraint names so Alembic autogenerate doesn't produce
    # env-dependent, anonymous constraints that drift between environments.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: cuid_generator()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Optimistic concurrency: SQLAlchemy bumps this on every UPDATE flush and
    # raises StaleDataError on concurrent writers.
    version_id: Mapped[int] = mapped_column(default=1, nullable=False)
    __mapper_args__ = {"version_id_col": version_id}  # noqa: RUF012
