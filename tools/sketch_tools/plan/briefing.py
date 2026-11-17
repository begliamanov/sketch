"""The skills an agent must read first, from the config and the story's extra skills."""

from __future__ import annotations

import re
from typing import Callable, List, Sequence, Set, Tuple

from sketch_tools.core.config_file import parse_config, parse_list
from sketch_tools.core.errors import DataError, UsageError

ROLES_WITH_SKILLS = ("task-writer", "test-writer", "implementer", "reviewer", "story-reviewer")
ROLES_WITHOUT_SKILLS = ("tester", "pr-agent", "retro-agent")


def parse_extra_skills(value: str) -> List[str]:
    """The paths in a state file's `extra_skills` value: `none`, or paths separated by commas or
    spaces."""
    text = value.strip()
    if text in ("", "none"):
        return []
    return [part for part in re.split(r"[,\s]+", text) if part]


def brief_skills(
    config_text: str, role: str, extra: Sequence[str], exists: Callable[[str], bool]
) -> Tuple[List[str], List[str]]:
    """(paths, problems): `common`, then the role's own list, then the story's extra skills, each
    once, in that order. A role that never gets skills (tester, pr-agent, retro-agent) gets none.
    Raises UsageError for an unknown role, DataError when the config lacks the role or a list."""
    known = ROLES_WITH_SKILLS + ROLES_WITHOUT_SKILLS
    if role not in known:
        raise UsageError("unknown role " + repr(role) + ": the roles are " + ", ".join(known))
    if role in ROLES_WITHOUT_SKILLS:
        return [], []

    config = parse_config(config_text)
    sources: List[Tuple[str, str]] = []
    for name in ("common", role):
        if name not in config.roles:
            raise DataError("the config has no skills role " + name + ": run config-check")
        paths, _problem = parse_list(config.roles[name])
        if paths is None:
            raise DataError("skills role " + name + " is not a list: run config-check")
        sources += [(path, "skills role " + name) for path in paths]
    for path in extra:
        if not (path.startswith("/") and path.endswith("/SKILL.md")):
            raise DataError("an extra skill must be an absolute path to a SKILL.md file (got " + repr(path) + ")")
        sources.append((path, "extra skill of the story"))

    seen: Set[str] = set()
    paths_out: List[str] = []
    problems: List[str] = []
    for path, origin in sources:
        if path in seen:
            continue
        seen.add(path)
        paths_out.append(path)
        if not exists(path):
            problems.append("skill file does not exist: " + path + " (" + origin + ")")
    return paths_out, problems
