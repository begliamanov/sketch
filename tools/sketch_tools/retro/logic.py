"""Pure retro logic: the rule from `/sketch` that says whether a retro is recommended."""

from __future__ import annotations

from typing import List

from sketch_tools.core.errors import UsageError

DEFAULT_FIRST_STORIES = 3
DEFAULT_MAX_LINES = 20
DEFAULT_MAX_COMMENTS = 10


def _plural(count: int, word: str) -> str:
    return str(count) + " " + word + ("" if count == 1 else "s")


def recommend(
    story: int, flags: int, caps: int, lines_changed: int, comments: int,
    first_stories: int = DEFAULT_FIRST_STORIES, max_lines: int = DEFAULT_MAX_LINES,
    max_comments: int = DEFAULT_MAX_COMMENTS,
) -> List[str]:
    """The reasons a retro is recommended, one message each. Empty means nothing is notable."""
    if story < 1:
        raise UsageError("story must be 1 or more")
    for name, value in (("flags", flags), ("caps", caps), ("lines changed", lines_changed), ("comments", comments)):
        if value < 0:
            raise UsageError(name + " cannot be negative")
    reasons: List[str] = []
    if story <= first_stories:
        reasons.append("story " + str(story) + " is one of the first " + str(first_stories))
    if flags > 0:
        reasons.append(_plural(flags, "flagged task"))
    if caps > 0:
        reasons.append(_plural(caps, "cap hit"))
    if lines_changed > max_lines:
        reasons.append("you changed " + str(lines_changed) + " lines after the PR (more than " + str(max_lines) + ")")
    if comments > max_comments:
        reasons.append(_plural(comments, "review comment") + " (more than " + str(max_comments) + ")")
    return reasons
