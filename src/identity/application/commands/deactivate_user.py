"""Deactivating a member — reversible, unlike a delete."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class DeactivateUserCommand(Command):
    directory_id: str
    user_id: str
    actor_id: str
