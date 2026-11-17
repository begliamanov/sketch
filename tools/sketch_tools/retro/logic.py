"""Pure retro logic: the rule from `/sketch` that says whether a retro is recommended."""

from __future__ import annotations

from typing import List

DEFAULT_FIRST_STORIES = 3
DEFAULT_MAX_LINES = 20
DEFAULT_MAX_COMMENTS = 10


def recommend(
    story: int, flags: int, caps: int, lines_changed: int, comments: int,
    first_stories: int = DEFAULT_FIRST_STORIES, max_lines: int = DEFAULT_MAX_LINES,
    max_comments: int = DEFAULT_MAX_COMMENTS,
) -> List[str]:
    """The reasons a retro is recommended, one message each. Empty means nothing is notable."""
    raise NotImplementedError
