"""What the tracker still needs, from the tasks file and the issues that are already there."""

from __future__ import annotations

from typing import Any, Dict, List


def parse_issue_facts(text: str) -> Dict[str, Any]:
    """Read and validate the tracker facts: `{"issues": [{"number": 120, "title": "..."}], "links":
    [{"blocked": "t-2", "by": "t-1"}]}`. Raises UsageError for anything wrong."""
    raise NotImplementedError


def issues_todo(tasks_text: str, facts: Dict[str, Any]) -> List[str]:
    """`have` and `todo` lines for the story issue, each task issue and each blocking link, in that
    order. Raises DataError for a tasks file with problems or two issues for one task."""
    raise NotImplementedError
