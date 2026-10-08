from dataclasses import dataclass

from core.application import Command
from identity.domain.value_objects.location import Location
from punch.domain import EntrySource


@dataclass(frozen=True)
class CreateTimeEntryCommand(Command):
    """Punch for the employee of the connected account.

    The direction (IN / OUT) and the location confidence are decided by the
    handler, never by the client.
    """

    user_id: str
    location: Location
    source: EntrySource
    idempotency_key: str | None = None
    wifi_identifier: str | None = None
