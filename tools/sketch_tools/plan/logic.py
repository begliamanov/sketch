"""Pure plan logic: check `tasks.md` and `config.md`, and work out the run order. No file access
(the config check is given a function that says whether a skill file exists)."""

from __future__ import annotations

from typing import Callable, List, Sequence

DEFAULT_MIN_TASKS = 3
DEFAULT_MAX_TASKS = 8


def check_tasks(
    text: str, min_tasks: int = DEFAULT_MIN_TASKS, max_tasks: int = DEFAULT_MAX_TASKS
) -> List[str]:
    """Every problem in a tasks.md, one message each. Empty list means valid."""
    raise NotImplementedError


def order_tasks(text: str, flagged: Sequence[str] = (), done: Sequence[str] = ()) -> List[str]:
    """The run order from the table's blocked_by: `run t-N` lines in order, then `skip t-N (blocked
    by ...)` lines for tasks that cannot run because a blocker is flagged or skipped. Tasks in
    `done` are satisfied blockers and are not run again. Raises DataError for a damaged table or a
    cycle, UsageError for an id that is not in the table."""
    raise NotImplementedError


def check_config(text: str, exists: Callable[[str], bool]) -> List[str]:
    """Every problem in a config.md, one message each. `exists` says whether a skill file exists."""
    raise NotImplementedError
