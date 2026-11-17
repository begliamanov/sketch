"""Read `config.md` into plain parts. It only splits the text; deciding what is wrong is the job
of the tool that uses it (`plan config-check`). Format: core/skills/tune-skills/SKILL.md, step 7."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

FIRST_LINE = "# sketch config"
_TOP = re.compile(r"([a-z_]+):[ ]?(.*)")
_ROLE = re.compile(r"  ([a-z-]+):[ ]?(.*)")


@dataclass
class ConfigFile:
    first_line_ok: bool
    keys: Dict[str, str] = field(default_factory=dict)
    key_counts: Dict[str, int] = field(default_factory=dict)
    has_skills: bool = False
    roles: Dict[str, str] = field(default_factory=dict)
    role_counts: Dict[str, int] = field(default_factory=dict)
    stray: List[str] = field(default_factory=list)  # lines that are neither key, role nor blank


def parse_config(text: str) -> ConfigFile:
    lines = text.split("\n")
    config = ConfigFile(bool(lines) and lines[0] == FIRST_LINE)
    in_skills = False
    for line in lines[1:]:
        if not line.strip():
            continue
        if line.rstrip() == "skills:":
            config.has_skills = True
            in_skills = True
            continue
        role = _ROLE.fullmatch(line) if in_skills else None
        if role:
            name = role.group(1)
            config.role_counts[name] = config.role_counts.get(name, 0) + 1
            config.roles.setdefault(name, role.group(2).strip())
            continue
        top = _TOP.fullmatch(line)
        if top and not line.startswith(" "):
            in_skills = False
            name = top.group(1)
            config.key_counts[name] = config.key_counts.get(name, 0) + 1
            config.keys.setdefault(name, top.group(2).strip())
            continue
        config.stray.append(line)
    return config


def parse_list(value: str) -> Tuple[Optional[List[str]], Optional[str]]:
    """`[a, b]` -> (["a", "b"], None). Not a list -> (None, "not a list"). A trailing or doubled
    comma -> (items without the empty ones, "has an empty item")."""
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None, "not a list"
    inner = value[1:-1].strip()
    if not inner:
        return [], None
    parts = [part.strip() for part in inner.split(",")]
    items = [part for part in parts if part]
    return items, ("has an empty item" if len(items) != len(parts) else None)
