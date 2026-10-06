"""Removing a member's password — they then log in with an emailed code."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class ClearUserPasswordCommand(Command):
    user_id: str
    actor_id: str
