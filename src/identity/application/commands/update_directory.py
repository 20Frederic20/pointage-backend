"""Renaming the workspace."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class UpdateDirectoryCommand(Command):
    name: str | None = None
    code: str | None = None
