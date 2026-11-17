"""One valid example report per role, for the report tests to copy and break."""

import copy
from typing import Any, Dict

SKILLS = [
    {"path": "/skills/kotlin/SKILL.md", "rule": "prefer immutable state"},
    {"path": "/skills/glossary/SKILL.md", "none_applies": "no new terms in this task"},
]

# role -> (scope, a valid report)
EXAMPLES: Dict[str, Any] = {
    "implementer": ("t-3", {
        "mode": "implement",
        "outcome": "done",
        "commits": ["t-3: add the offline banner"],
        "assumptions": ["used the existing NoteRepository (brief said new)"],
        "doubts": [],
        "skills_applied": SKILLS,
    }),
    "test-writer": ("t-3", {
        "mode": "write",
        "outcome": "done",
        "files": ["Tests/BannerTests.swift"],
        "tests_per_criterion": {"1": 3, "2": 2},
        "verification": {
            "command": "./gradlew test --tests BannerTests",
            "failing": ["BannerTests.hides the banner when online"],
        },
        "assumptions": [],
        "doubts": [],
        "skills_applied": SKILLS,
    }),
    "reviewer": ("t-3", {
        "outcome": "done",
        "verdict": "SATISFIED",
        "must_fix": [],
        "nice_to_have": ["rename tmp to cachedNotes"],
        "criteria_coverage": [
            {"criterion": "1", "test": "BannerTests.shows the banner offline", "status": "OK"},
            {"criterion": "2", "test": "BannerTests.hides the banner online", "status": "OK"},
        ],
        "assumptions": [],
        "doubts": [],
        "skills_applied": SKILLS,
    }),
    "story-reviewer": ("story-2", {
        "model": "Opus",
        "outcome": "done",
        "verdict": "SATISFIED",
        "must_fix": [],
        "nice_to_have": ["README does not mention the cache"],
        "brief_delivered": {"status": "YES", "missing": []},
        "tester_result": "PASS",
        "assumptions": [],
        "doubts": [],
        "skills_applied": SKILLS,
    }),
    "tester": ("story-2", {
        "mode": "full",
        "result": "PASS",
        "branch": "story-2-offline-notes",
        "sha": "a35c24b",
        "command": "./gradlew testDebugUnitTest",
        "log": ".sketch/logs/20261116-full.log",
        "counts": {"passed": 42, "failed": 0, "skipped": 1},
    }),
    "task-writer": ("story-2", {
        "mode": "draft",
        "outcome": "done",
        "tasks": [
            {"id": "t-1", "title": "Read notes from cache", "blocked_by": "none", "scenarios": 3},
            {"id": "t-2", "title": "Sync on reconnect", "blocked_by": "t-1", "scenarios": 3},
        ],
        "assumptions": [],
        "doubts": ["t-2 may be too big"],
        "skills_applied": SKILLS,
    }),
    "pr-agent": ("story-2", {
        "outcome": "done",
        "pr": "45",
        "head_sha": "a35c24b",
    }),
    "retro-agent": ("story-2", {
        "outcome": "done",
        "draft_path": ".sketch/retro/S2.md",
        "overview": "Two flags, both from the same missing glossary term. Nothing else notable.",
    }),
}

TASK_ROLES = ("implementer", "test-writer", "reviewer")
STORY_ROLES = ("story-reviewer", "tester", "task-writer", "pr-agent", "retro-agent")
ROLES_WITH_SKILLS = ("implementer", "test-writer", "reviewer", "story-reviewer", "task-writer")

PUBLISH = {
    "mode": "publish",
    "outcome": "done",
    "story_issue": 120,
    "task_issues": {"t-1": 121, "t-2": 122},
    "already_there": [],
    "assumptions": [],
    "doubts": [],
    "skills_applied": SKILLS,
}


def example(role: str) -> Dict[str, Any]:
    """A fresh valid report for the role."""
    return copy.deepcopy(EXAMPLES[role][1])


def scope_of(role: str) -> str:
    return str(EXAMPLES[role][0])


def with_changes(role: str, **changes: Any) -> Dict[str, Any]:
    """The example with some fields replaced; a value of `...` deletes the field."""
    report = example(role)
    for key, value in changes.items():
        if value is ...:
            report.pop(key, None)
        else:
            report[key] = value
    return report
