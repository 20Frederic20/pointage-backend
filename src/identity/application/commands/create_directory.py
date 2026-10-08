"""Create a directory, optionally inside a parent directory. Its sites are
created afterwards (``CreateSiteCommand``)."""

from dataclasses import dataclass

from core.application import Command


@dataclass(frozen=True)
class CreateDirectoryCommand(Command):
    name: str
    code: str
    parent_directory_id: str | None = None
