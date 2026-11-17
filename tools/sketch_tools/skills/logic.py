"""Pure skills logic: read the front matter of a SKILL.md. No file access."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Optional

_KEY = re.compile(r"([A-Za-z_][\w-]*):[ \t]*(.*)")


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: str


def _one_line(text: str) -> str:
    """Whitespace of any kind, tabs and line breaks included, becomes single spaces."""
    return " ".join(text.split())


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _front_matter(text: str) -> Dict[str, str]:
    """The top-level `key: value` pairs between the first two `---` lines. A value continues on
    the indented lines under it (a folded `>` description, or a long one wrapped by hand)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end: Optional[int] = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}
    fields: Dict[str, str] = {}
    key: Optional[str] = None
    for line in lines[1:end]:
        match = _KEY.fullmatch(line) if not line.startswith((" ", "\t")) else None
        if match:
            key, value = match.group(1), match.group(2).strip()
            fields[key] = "" if value in (">", ">-", "|", "|-") else value
        elif key is not None and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def parse_skill(path: str, text: str) -> Skill:
    """The name and description from the `---` front matter of a SKILL.md. Without a `name` the
    name of its folder is used; a missing description is empty."""
    fields = _front_matter(text)
    name = _one_line(_unquote(fields.get("name", ""))) or os.path.basename(os.path.dirname(path))
    return Skill(name, _one_line(_unquote(fields.get("description", ""))), path)
