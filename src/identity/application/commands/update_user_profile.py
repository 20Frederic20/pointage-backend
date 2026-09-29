"""Editing one's own (or, for admins, another member's) profile."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class UpdateUserProfileCommand(Command):
    user_id: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
