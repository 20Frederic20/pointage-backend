from dataclasses import dataclass

from core.application import Command
from identity.domain.value_objects.location import Location


@dataclass(frozen=True)
class CreateAssistedTimeEntryCommand(Command):
    """Punch for the employee whose number is typed, from the caller's phone.

    ``actor_user_id`` (the phone's owner, from the token) is recorded as the
    assistant. The direction (IN / OUT) is decided by the handler.
    """

    actor_user_id: str
    employee_number: str
    location: Location
    photo: bytes
    photo_content_type: str
    idempotency_key: str
    wifi_identifier: str | None = None
