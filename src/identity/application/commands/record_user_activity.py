"""Presence telemetry: the auth context fires this on login/refresh."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class RecordUserActivityCommand(Command):
    """
    Best-effort: stamp ``last_active_at``; nothing to roll back on failure.
    """

    user_id: str
