from dataclasses import dataclass

from core.application import DTO


@dataclass(frozen=True)
class OutgoingEmailDTO(DTO):
    """An email ready to send. Carries a plaintext login code: it lives only
    in memory, between the handler and the ``EmailSender``."""

    to: str
    subject: str
    body: str
