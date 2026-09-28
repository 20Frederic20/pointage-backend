"""Renaming the workspace."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class UpdateDirectoryCommand(Command):
    directory_id: str
    name: str
