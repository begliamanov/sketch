"""What the tracker still needs, from the tasks file and the issues that are already there."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.plan import tasks_file
from sketch_tools.plan.logic import check_tasks

_TASK_ID = re.compile(r"t-\d+")
_TASK_TITLE = re.compile(r"(t-\d+):")


def parse_issue_facts(text: str) -> Dict[str, Any]:
    """Read and validate the tracker facts: `{"issues": [{"number": 120, "title": "..."}], "links":
    [{"blocked": "t-2", "by": "t-1"}]}`. Raises UsageError for anything wrong."""
    try:
        facts = json.loads(text)
    except ValueError as err:
        raise UsageError("the facts are not valid JSON: " + str(err)) from None
    if not isinstance(facts, dict):
        raise UsageError("the facts must be a JSON object")
    for key in facts:
        if key not in ("issues", "links"):
            raise UsageError("unknown fact: " + key)
    issues, links = facts.get("issues", []), facts.get("links", [])
    if not isinstance(issues, list):
        raise UsageError("issues must be a list")
    for index, issue in enumerate(issues):
        label = "issues[" + str(index) + "]"
        if not isinstance(issue, dict) or set(issue) != {"number", "title"}:
            raise UsageError(label + " must be an object with a number and a title")
        number = issue["number"]
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise UsageError(label + ".number must be a whole number, 1 or more")
        if not isinstance(issue["title"], str) or not issue["title"].strip():
            raise UsageError(label + ".title must be text")
    if not isinstance(links, list):
        raise UsageError("links must be a list")
    for index, link in enumerate(links):
        label = "links[" + str(index) + "]"
        if not isinstance(link, dict) or set(link) != {"blocked", "by"}:
            raise UsageError(label + " must be an object with blocked and by")
        for key in ("blocked", "by"):
            if not isinstance(link[key], str) or not _TASK_ID.fullmatch(link[key]):
                raise UsageError(label + "." + key + " must be a task id like t-3")
    return {"issues": issues, "links": links}


def issues_todo(tasks_text: str, facts: Dict[str, Any]) -> List[str]:
    """`have` and `todo` lines for the story issue, each task issue and each blocking link, in that
    order. Raises DataError for a tasks file with problems or two issues for one task."""
    problems = check_tasks(tasks_text)
    if problems:
        raise DataError("the tasks file has problems, run tasks-check first: " + problems[0])
    parsed = tasks_file.parse_tasks(tasks_text)
    first = next(line for line in tasks_text.split("\n") if line.strip())
    match = tasks_file.FIRST_LINE.fullmatch(first)
    assert match is not None  # check_tasks accepted the first line
    story_number = match.group(1)
    story_title = "Story " + story_number + ": " + first.split(": ", 1)[1]

    story_issues: List[int] = []
    task_issues: Dict[str, List[int]] = {}
    for issue in facts.get("issues", []):
        title = issue["title"]
        if title.startswith("Story " + story_number + ":"):
            story_issues.append(issue["number"])
        task = _TASK_TITLE.match(title)
        if task:
            task_issues.setdefault(task.group(1), []).append(issue["number"])
    if len(story_issues) > 1:
        raise DataError("two issues for the story: " + " and ".join("#" + str(n) for n in story_issues))
    for task_id, numbers in task_issues.items():
        if len(numbers) > 1:
            raise DataError("two issues for " + task_id + ": " + " and ".join("#" + str(n) for n in numbers))

    lines: List[str] = []
    lines.append(("have story: #" + str(story_issues[0])) if story_issues else ("todo story: " + story_title))
    rows = [row for row in parsed.rows]
    for task_id, title, _blocked, _scenarios in rows:
        if task_id in task_issues:
            lines.append("have task " + task_id + ": #" + str(task_issues[task_id][0]))
        else:
            lines.append("todo task " + task_id + ": " + task_id + ": " + title)
    existing = {(link["blocked"], link["by"]) for link in facts.get("links", [])}
    for task_id, _title, blocked, _scenarios in rows:
        for blocker in ([] if blocked == "none" else [part.strip() for part in blocked.split(",")]):
            lines.append(("have" if (task_id, blocker) in existing else "todo") + " link " + task_id + " " + blocker)
    return lines
