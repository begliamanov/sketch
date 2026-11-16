"""Pure journal logic: validate an event and format its line. No file access."""

from __future__ import annotations

import re
from datetime import datetime

from sketch_tools.core.errors import UsageError

ENTRY_TYPES = ("FLAG", "CAP", "ASSUME", "REVIEW", "NOTE", "EDIT", "CONTEXT", "STOP")

ME_MARKER = "[me] "
_TYPE_WIDTH = max(len(t) for t in ENTRY_TYPES)
_TASK_WIDTH = 3
_STORY = re.compile(r"S\d+")
_TASK = re.compile(r"t-\d+|-")


def format_entry(
    entry_type: str, story: str, task: str, text: str, when: datetime, me: bool = False
) -> str:
    """Return one journal line, without a trailing newline. Raises UsageError on bad input.

    Shape: ``<YYYY-MM-DD HH:MM>  S<story> <task>  <TYPE>  <text>``, with the task and the type
    padded so every line starts its type and its text in the same columns. The text is kept
    exactly as given.
    """
    if entry_type not in ENTRY_TYPES:
        raise UsageError(
            "type must be one of " + " ".join(ENTRY_TYPES) + " (got " + repr(entry_type) + ")"
        )
    if not _STORY.fullmatch(story):
        raise UsageError("story must look like S2 (got " + repr(story) + ")")
    if not _TASK.fullmatch(task):
        raise UsageError("task must look like t-2, or - for the whole story (got " + repr(task) + ")")
    if not text.strip():
        raise UsageError("text must not be empty")
    if "\n" in text or "\r" in text:
        raise UsageError("text must be one line")

    stamp = when.strftime("%Y-%m-%d %H:%M")
    marker = ME_MARKER if me else ""
    return (
        stamp + "  " + story + " " + task.ljust(_TASK_WIDTH) + "  "
        + entry_type.ljust(_TYPE_WIDTH) + " " + marker + text
    )
