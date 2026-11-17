"""Pure skills logic: read the front matter of a SKILL.md. No file access."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: str


def parse_skill(path: str, text: str) -> Skill:
    """The name and description from the `---` front matter of a SKILL.md. Without a `name` the
    name of its folder is used; a missing description is empty."""
    raise NotImplementedError
