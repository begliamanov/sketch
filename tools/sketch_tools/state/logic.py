"""Pure state logic: read, edit and check the text of state.md. No file access.

Edits are minimal: only the one line or table cell that changes is touched, so everything else
(order, alignment, the Flags section) stays byte for byte.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


def set_header(text: str, key: str, value: str) -> str:
    """Set one `key: value` line. Raises UsageError for a bad key or value, RefusedError for a
    counter (use bump), DataError when the file has no such line."""
    raise NotImplementedError


def set_task(text: str, task_id: str, field: str, value: str) -> str:
    """Set one cell in a task row. Same errors as set_header."""
    raise NotImplementedError


def bump(text: str, key: str, task_id: Optional[str] = None) -> Tuple[str, str, str]:
    """Increase one counter by one. Returns (new text, old value, new value).
    Raises RefusedError at the cap, UsageError for a non-counter, DataError for a bad counter."""
    raise NotImplementedError


def check(text: str) -> List[str]:
    """Return every problem found, one message per problem. Empty list means valid."""
    raise NotImplementedError
