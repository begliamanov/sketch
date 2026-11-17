"""The skills an agent must read first, from the config and the story's extra skills."""

from __future__ import annotations

from typing import Callable, List, Sequence, Tuple


def parse_extra_skills(value: str) -> List[str]:
    """The paths in a state file's `extra_skills` value: `none`, or paths separated by commas or
    spaces."""
    raise NotImplementedError


def brief_skills(
    config_text: str, role: str, extra: Sequence[str], exists: Callable[[str], bool]
) -> Tuple[List[str], List[str]]:
    """(paths, problems): `common`, then the role's own list, then the story's extra skills, each
    once, in that order. A role that never gets skills (tester, pr-agent, retro-agent) gets none.
    Raises UsageError for an unknown role, DataError when the config lacks the role or a list."""
    raise NotImplementedError
