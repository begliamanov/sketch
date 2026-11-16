"""The state file's schema, in one place. `set`, `bump` and `check` all read it, so they cannot
disagree. Source of truth for the format: core/state-format.md."""

from __future__ import annotations

import re
from typing import Callable, Dict, Optional, Tuple

TITLE_LINE = "# Story state"
TASKS_HEADING = "## Tasks"

PHASES = ("sketch", "tasks", "baseline", "task-loop", "story-end", "pr", "waiting-review", "done")
TASK_STATUSES = ("pending", "tests-red", "green", "in-review", "done", "flagged")

# Header keys, in file order. All are required.
HEADER_KEYS = (
    "story", "title", "story_issue", "feature_branch", "story_branch", "phase", "last_step",
    "stopped", "pr", "pr_head_sha", "story_rounds", "extra_skills",
)
OPTIONAL_KEYS = ("stop_after_task",)  # allowed by `check`; `set` cannot add it (see the notes)
COUNTER_KEYS = ("story_rounds",)

TASK_COLUMNS = ("id", "issue", "title", "blocked_by", "status", "attempts", "review_rounds")
TASK_COUNTER_FIELDS = ("attempts", "review_rounds")
SETTABLE_TASK_FIELDS = ("issue", "title", "blocked_by", "status")

TASK_ID = re.compile(r"t-\d+")
COUNTER = re.compile(r"(\d+)/(\d+)")


def _one_line(key: str) -> Callable[[str], Optional[str]]:
    def rule(value: str) -> Optional[str]:
        if not value.strip() or "\n" in value or "\r" in value:
            return key + " must be one non-empty line"
        return None

    return rule


def _matching(key: str, pattern: str, description: str) -> Callable[[str], Optional[str]]:
    compiled = re.compile(pattern)

    def rule(value: str) -> Optional[str]:
        return None if compiled.fullmatch(value) else key + " must be " + description

    return rule


def _one_of(key: str, allowed: Tuple[str, ...]) -> Callable[[str], Optional[str]]:
    def rule(value: str) -> Optional[str]:
        return None if value in allowed else key + " must be one of " + " ".join(allowed)

    return rule


HEADER_RULES: Dict[str, Callable[[str], Optional[str]]] = {
    "story": _matching("story", r"\d+", "a number"),
    "title": _one_line("title"),
    "story_issue": _matching("story_issue", r"\d+|none", "a number or none"),
    "feature_branch": _one_line("feature_branch"),
    "story_branch": _one_line("story_branch"),
    "phase": _one_of("phase", PHASES),
    "last_step": _one_line("last_step"),
    "stopped": _matching(
        "stopped", r"no|failure: \S.*|manual: \S.*", "no, failure: <reason> or manual: <reason>"
    ),
    "pr": _matching("pr", r"none|\d+|https?://\S+", "none, a number or a URL"),
    "pr_head_sha": _matching(
        "pr_head_sha", r"none|[0-9a-f]{7,40}", "none or a git sha (7 to 40 hex characters)"
    ),
    "extra_skills": _one_line("extra_skills"),
    "stop_after_task": _matching("stop_after_task", r"yes", "yes"),
}

_TITLE_RULE = _one_line("title")


def _title_rule(value: str) -> Optional[str]:
    problem = _TITLE_RULE(value)
    if problem:
        return problem
    return "title must not contain |" if "|" in value else None


TASK_RULES: Dict[str, Callable[[str], Optional[str]]] = {
    "issue": _matching("issue", r"\d+|none", "a number or none"),
    "title": _title_rule,
    "blocked_by": _matching("blocked_by", r"none|t-\d+(,t-\d+)*", "none or ids like t-1,t-2"),
    "status": _one_of("status", TASK_STATUSES),
}
