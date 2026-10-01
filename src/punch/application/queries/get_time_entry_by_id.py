

from core.application import Query
from punch.application.dtos import TimeEntryDTO


class GetTimeEntryByIdQuery(Query):
    """Get a time entry by its ID."""

    time_entry_id: str

    Result = TimeEntryDTO | None