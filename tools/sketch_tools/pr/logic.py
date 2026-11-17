"""Pure PR logic: render the description, check the PR JSON and the description. No file access.

The description follows the template in core/agents/pr-agent.md. Flags and unresolved items are
copied exactly; everything else is a short fixed shape, so the same state gives the same text."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.state.logic import header_value, read_flags, read_tasks

DEFAULT_MAX_LINES = 20
_MAX_SUMMARY_LINES = 3
_NICE_TO_HAVE_SHOWN = 3

_REQUIRED = ("summary", "tests_passed", "reviewer_model")
_LISTS = ("unresolved", "nice_to_have", "manual_checks", "differs", "wip_commits")


def parse_extras(text: str) -> Dict[str, Any]:
    """Read and validate the extras JSON. Returns every key, with defaults for the optional ones.
    Raises UsageError for anything wrong."""
    try:
        data = json.loads(text)
    except ValueError as err:
        raise UsageError("the extras file is not valid JSON: " + str(err)) from None
    if not isinstance(data, dict):
        raise UsageError("the extras file must be a JSON object")
    for key in data:
        if key not in _REQUIRED + _LISTS:
            raise UsageError("unknown key in the extras file: " + key)
    for key in _REQUIRED:
        if key not in data:
            raise UsageError("the extras file needs " + key)

    summary = data["summary"]
    if not isinstance(summary, str) or not summary.strip():
        raise UsageError("summary must be a non-empty string")
    if len(summary.strip().split("\n")) > _MAX_SUMMARY_LINES:
        raise UsageError("summary must be at most " + str(_MAX_SUMMARY_LINES) + " lines")
    passed = data["tests_passed"]
    if isinstance(passed, bool) or not isinstance(passed, int) or passed < 0:
        raise UsageError("tests_passed must be a number, 0 or more")
    model = data["reviewer_model"]
    if not isinstance(model, str) or not model.strip():
        raise UsageError("reviewer_model must be a non-empty string")

    result: Dict[str, Any] = {"summary": summary.strip(), "tests_passed": passed, "reviewer_model": model}
    for key in _LISTS:
        items = data.get(key, [])
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise UsageError(key + " must be a list of strings")
        if any(not item.strip() for item in items):
            raise UsageError(key + " has an empty item")
        if any("\n" in item or "\r" in item for item in items):
            raise UsageError(key + " items must be one line")
        result[key] = list(items)
    return result


def _story_facts(state_text: str) -> Tuple[str, str, str, int]:
    values = {}
    for key in ("story", "title", "story_issue", "story_rounds"):
        value = header_value(state_text, key)
        if value is None:
            raise DataError("the state file has no " + key + ": line")
        values[key] = value
    match = re.fullmatch(r"(\d+)/\d+", values["story_rounds"])
    if not match:
        raise DataError('story_rounds "' + values["story_rounds"] + '" is not used/cap, like 1/3')
    return values["story"], values["title"], values["story_issue"], int(match.group(1))


def _task_text(task: Dict[str, str]) -> str:
    issue = "" if task["issue"] == "none" else "#" + task["issue"] + " "
    status = {"done": "✓", "flagged": "flagged"}.get(task["status"], task["status"])
    return issue + task["title"] + " " + status


def render_body(state_text: str, extras: Dict[str, Any], max_lines: int = DEFAULT_MAX_LINES) -> str:
    """The PR description, from the state file and the (already validated) extras. Raises DataError
    for a damaged state file or when the description is over the line limit."""
    story, title, issue, rounds = _story_facts(state_text)
    tasks = read_tasks(state_text)
    flags = read_flags(state_text)

    flag_lines = list(flags)
    flag_lines += ["- Unresolved: " + item for item in extras["unresolved"]]
    flag_lines += ["- WIP commit never followed by a completed step: " + item for item in extras["wip_commits"]]

    heading = "Story " + story + ": " + title + ("" if issue == "none" else " (#" + issue + ")")
    verdict = "unresolved items below" if extras["unresolved"] else "nothing blocking"
    counted: List[List[str]] = [
        [heading],
        extras["summary"].split("\n"),
        [
            "Tasks: " + " · ".join(_task_text(task) for task in tasks),
            "Tests: " + str(extras["tests_passed"]) + " pass. " + extras["reviewer_model"]
            + " reviewed it, " + str(rounds) + " round(s), " + verdict
            + ". Flags: " + ("see below" if flag_lines else "none") + ".",
        ],
    ]
    blocks: List[List[str]] = list(counted)
    if flag_lines:
        blocks.append(["Flags:"] + flag_lines)  # not counted towards the limit
    if extras["manual_checks"]:
        block = ["Check by hand (tests can't see these):"] + ["- " + i for i in extras["manual_checks"]]
        blocks.append(block)
        counted.append(block)
    nice = extras["nice_to_have"]
    if nice:
        block = ["Small stuff, not blocking:"] + ["- " + i for i in nice[:_NICE_TO_HAVE_SHOWN]]
        blocks.append(block)
        counted.append(block)
        rest = nice[_NICE_TO_HAVE_SHOWN:]
        if rest:  # folded away, not counted
            noun = "nice-to-have" if len(rest) == 1 else "nice-to-haves"
            blocks.append(
                ["<details><summary>" + str(len(rest)) + " more " + noun + "</summary>", ""]
                + ["- " + i for i in rest] + ["", "</details>"]
            )
    if extras["differs"]:
        block = ["Differs from the plan:"] + ["- " + i for i in extras["differs"]]
        blocks.append(block)
        counted.append(block)

    count = sum(1 for block in counted for line in block if line.strip())
    if count > max_lines:
        raise DataError(
            "the description is " + str(count) + " lines (limit " + str(max_lines) + "): shorten the "
            "summary, the check-by-hand items or the differs items"
        )
    return "\n\n".join("\n".join(block) for block in blocks) + "\n"


def check_base(json_text: str, base: str, head: Optional[str] = None) -> List[str]:
    """Check `gh pr view --json ...` or `glab mr view --output json` output. Raises UsageError
    when the text is not a JSON object."""
    try:
        data = json.loads(json_text)
    except ValueError:
        raise UsageError("the PR text is not valid JSON") from None
    if not isinstance(data, dict):
        raise UsageError("the PR JSON must be an object")
    actual_base = data.get("baseRefName") or data.get("target_branch")
    actual_head = data.get("headRefName") or data.get("source_branch")
    state = data.get("state")
    problems: List[str] = []
    if not actual_base:
        problems.append("no base branch in the JSON (expected baseRefName or target_branch)")
    elif actual_base != base:
        problems.append('base is "' + str(actual_base) + '", expected "' + base + '"')
    if head is not None:
        if not actual_head:
            problems.append("no head branch in the JSON (expected headRefName or source_branch)")
        elif actual_head != head:
            problems.append('head is "' + str(actual_head) + '", expected "' + head + '"')
    if isinstance(state, str) and state.lower() not in ("open", "opened"):
        problems.append('PR state is "' + state + '", expected open')
    return problems


def check_flags(
    body: str, state_text: str, extras: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Every flag in the state file, and every unresolved item and WIP commit in the extras, must
    appear in the description."""
    problems: List[str] = []
    for line in read_flags(state_text):
        text = line[2:]
        if text not in body:
            problems.append('flag "' + text + '" is not in the PR description')
    if extras:
        for key, label in (("unresolved", "unresolved item"), ("wip_commits", "WIP commit")):
            for item in extras.get(key, []):
                if item not in body:
                    problems.append(label + " is not in the PR description: " + item)
    return problems
