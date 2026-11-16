"""Pure journal logic: validate an event and format its line. No file access."""

from __future__ import annotations

from datetime import datetime

ENTRY_TYPES = ("FLAG", "CAP", "ASSUME", "REVIEW", "NOTE", "EDIT", "CONTEXT", "STOP")


def format_entry(
    entry_type: str, story: str, task: str, text: str, when: datetime, me: bool = False
) -> str:
    """Return one journal line, without a trailing newline. Raises UsageError on bad input."""
    raise NotImplementedError
