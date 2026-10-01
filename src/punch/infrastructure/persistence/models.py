from datetime import datetime

from geoalchemy2.types import Geography
from shapely.geometry import Point
from sqlalchemy import DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import ForeignKey

from core.infrastructure.database import BaseModel
from punch.domain import EntrySource, EntryType, LocationConfidence


class TimeEntryModel(BaseModel):
    __tablename__ = "time_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(32), ForeignKey("employees.id"), nullable=False)
    entry_type: Mapped[EntryType] = mapped_column(SAEnum(EntryType, native_enum=False, length=16), nullable=False)
    occured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[Point] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    location_confidence: Mapped[LocationConfidence] = mapped_column(SAEnum(LocationConfidence, native_enum=False, length=16), nullable=False)
    source: Mapped[EntrySource] = mapped_column(SAEnum(EntrySource, native_enum=False, length=16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    wifi_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)