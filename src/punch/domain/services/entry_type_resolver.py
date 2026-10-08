from datetime import datetime, timedelta

from ..entities import TimeEntry
from ..value_objects import EntryType


class EntryTypeResolver:
    """Decide whether a punch is an IN or an OUT: the employee never chooses."""

    # ponytail: one fixed window for every employee. An IN older than this is
    # a forgotten OUT: the next punch opens a new day (IN) and the gap is left
    # to the anomaly checks. Move it to the time profile when shifts last longer.
    MAX_SHIFT = timedelta(hours=16)

    @classmethod
    def resolve(cls, last_entry: TimeEntry | None, now: datetime) -> EntryType:
        """OUT after a recent IN, IN otherwise."""
        if (
            last_entry is not None
            and last_entry.entry_type == EntryType.IN
            and now - last_entry.occured_at < cls.MAX_SHIFT
        ):
            return EntryType.OUT
        return EntryType.IN
