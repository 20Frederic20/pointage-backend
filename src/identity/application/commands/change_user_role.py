"""Changing a member's role within their workspace."""

from dataclasses import dataclass

from core.application import Command

from ...domain.value_objects import Role


@dataclass(frozen=True)
class ChangeUserRoleCommand(Command):
    directory_id: str
    user_id: str
    role: Role
    changed_by: str
