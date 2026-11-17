"""Pure state logic: read, edit and check the text of state.md. No file access.

Edits are minimal: only the one line or table cell that changes is touched, so everything else
(order, alignment, the Flags section) stays byte for byte.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sketch_tools.core.errors import DataError, RefusedError, UsageError
from sketch_tools.state import schema

_KEY_LINE = re.compile(r"([a-z_]+):(?: (.*))?")


@dataclass
class _Row:
    line: int  # index into the list of lines
    cells: List[str]  # raw cells, including their padding


def _split(text: str) -> List[str]:
    return text.split("\n")


def _header_end(lines: List[str]) -> int:
    """Index of the first `## ` heading, or the number of lines if there is none."""
    for index, line in enumerate(lines):
        if line.startswith("## "):
            return index
    return len(lines)


def _header_lines(lines: List[str]) -> Dict[str, List[int]]:
    found: Dict[str, List[int]] = {}
    for index in range(_header_end(lines)):
        match = _KEY_LINE.fullmatch(lines[index])
        if match:
            found.setdefault(match.group(1), []).append(index)
    return found


def _header_value(lines: List[str], index: int) -> str:
    match = _KEY_LINE.fullmatch(lines[index])
    return (match.group(2) or "") if match else ""


def _table(lines: List[str]) -> Tuple[Optional[List[str]], List[_Row]]:
    """The task table: its header cells (stripped) or None, and its data rows."""
    start = None
    for index, line in enumerate(lines):
        if line == schema.TASKS_HEADING:
            start = index
            break
    if start is None:
        return None, []
    header: Optional[List[str]] = None
    rows: List[_Row] = []
    position = 0
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = line.split("|")[1:-1]
        if position == 0:
            header = [cell.strip() for cell in cells]
        elif position >= 2:  # position 1 is the |---| separator
            rows.append(_Row(index, cells))
        position += 1
    return header, rows


def _find_row(rows: List[_Row], task_id: str) -> _Row:
    for row in rows:
        if row.cells and row.cells[0].strip() == task_id:
            return row
    raise UsageError("unknown task: " + task_id)


def _with_cell(row: _Row, column: int, value: str) -> str:
    raw = row.cells[column]
    padding = max(1, len(raw) - 1 - len(value))
    cells = list(row.cells)
    cells[column] = " " + value + " " * padding
    return "|" + "|".join(cells) + "|"


def _require_table(lines: List[str]) -> List[_Row]:
    header, rows = _table(lines)
    if header is None:
        raise DataError("the file has no " + schema.TASKS_HEADING + " section")
    return rows


def _join(lines: List[str]) -> str:
    return "\n".join(lines)


def set_header(text: str, key: str, value: str) -> str:
    """Set one `key: value` line. Raises UsageError for a bad key or value, RefusedError for a
    counter (use bump), DataError when the file has no such line."""
    if key in schema.COUNTER_KEYS:
        raise RefusedError(key + " is a counter: use bump, not set")
    if key not in schema.HEADER_KEYS:
        raise UsageError("unknown key: " + key)
    problem = schema.HEADER_RULES[key](value)
    if problem:
        raise UsageError(problem)
    lines = _split(text)
    where = _header_lines(lines).get(key)
    if not where:
        raise DataError("the file has no " + key + ": line")
    lines[where[0]] = key + ": " + value
    return _join(lines)


def _flags(lines: List[str]) -> Tuple[Optional[int], int, List[Tuple[int, str]]]:
    """The Flags section: (heading index or None, index just past the section, its `- ` lines)."""
    start = None
    for index, line in enumerate(lines):
        if line == schema.FLAGS_HEADING:
            start = index
            break
    if start is None:
        return None, len(lines), []
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    found = [(i, lines[i]) for i in range(start + 1, end) if lines[i].startswith("- ")]
    return start, end, found


def header_value(text: str, key: str) -> Optional[str]:
    """The value of a header line, or None when the file has no such line."""
    lines = _split(text)
    where = _header_lines(lines).get(key)
    return _header_value(lines, where[0]) if where else None


def _positive(name: str, value: int) -> int:
    if value < 1:
        raise UsageError(name + " must be a number of at least 1")
    return value


def new_story(
    story: str, title: str, feature_branch: str, extra_skills: str = "none",
    story_rounds_cap: int = schema.DEFAULT_STORY_ROUNDS_CAP,
) -> str:
    """The text of a fresh state file for a story. Raises UsageError for a bad value."""
    for key, value in (("story", story), ("title", title), ("feature_branch", feature_branch),
                       ("extra_skills", extra_skills)):
        problem = schema.HEADER_RULES[key](value)
        if problem:
            raise UsageError(problem)
    cap = _positive("story_rounds cap", story_rounds_cap)
    lines = [
        schema.TITLE_LINE,
        "story: " + story,
        "title: " + title,
        "story_issue: none",
        "feature_branch: " + feature_branch,
        "story_branch: none",
        "phase: tasks",
        "last_step: story brief approved",
        "stopped: no",
        "pr: none",
        "pr_head_sha: none",
        "story_rounds: 0/" + str(cap),
        "extra_skills: " + extra_skills,
        "stop_after_task: no",
        "",
        schema.TASKS_HEADING,
        schema.TASK_TABLE_HEADER,
        schema.TASK_TABLE_SEPARATOR,
        "",
        schema.FLAGS_HEADING,
        "",
    ]
    return _join(lines)


def _table_lines(lines: List[str]) -> List[int]:
    """Indexes of the `|` lines of the task table: header, separator, then the rows."""
    start = None
    for index, line in enumerate(lines):
        if line == schema.TASKS_HEADING:
            start = index
            break
    if start is None:
        raise DataError("the file has no " + schema.TASKS_HEADING + " section")
    found: List[int] = []
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            break
        if lines[index].startswith("|"):
            found.append(index)
    if len(found) < 2:
        raise DataError("the task table has no header and separator lines")
    return found


def add_task(
    text: str, task_id: str, title: str, blocked_by: str = "none", issue: str = "none",
    attempts_cap: int = schema.DEFAULT_ATTEMPTS_CAP,
    review_rounds_cap: int = schema.DEFAULT_REVIEW_ROUNDS_CAP,
) -> str:
    """Append a `pending` row to the task table. Raises UsageError for a bad value, RefusedError
    when the task already exists, DataError when the file has no task table."""
    if not schema.TASK_ID.fullmatch(task_id):
        raise UsageError("task id must look like t-5 (got " + repr(task_id) + ")")
    for field, value in (("title", title), ("blocked_by", blocked_by), ("issue", issue)):
        problem = schema.TASK_RULES[field](value)
        if problem:
            raise UsageError(problem)
    if task_id in blocked_by.split(","):
        raise UsageError(task_id + " cannot block itself")
    attempts = _positive("attempts cap", attempts_cap)
    reviews = _positive("review_rounds cap", review_rounds_cap)

    lines = _split(text)
    table = _table_lines(lines)
    header_cells = lines[table[0]].split("|")[1:-1]
    if len(header_cells) != len(schema.TASK_COLUMNS):
        raise DataError("the task table header does not have the expected columns")
    for index in table[2:]:
        first = lines[index].split("|")[1:2]
        if first and first[0].strip() == task_id:
            raise RefusedError(task_id + " already exists")

    values = [task_id, issue, title, blocked_by, "pending", "0/" + str(attempts), "0/" + str(reviews)]
    cells = [
        " " + value + " " * max(1, len(raw) - 1 - len(value))
        for raw, value in zip(header_cells, values)
    ]
    lines.insert(table[-1] + 1, "|" + "|".join(cells) + "|")
    return _join(lines)


def _phase_and_story(text: str) -> Tuple[str, str]:
    phase, story = header_value(text, "phase"), header_value(text, "story")
    if not phase:
        raise DataError("the state file has no phase: line")
    if not story:
        raise DataError("the state file has no story: line")
    return phase, story


def gate(text: Optional[str], pr_state: Optional[str] = None) -> Tuple[str, str]:
    """Can a new story start? Returns (decision, message): `go`, `mark-done` (the story's PR was
    merged: set the phase to done, then go) or `stop` with the reason. `text` is None when there is
    no state file. Raises UsageError for a PR state that is missing when it is needed or unknown,
    DataError for a state file without a phase."""
    if text is None:
        return "go", ""
    phase, story = _phase_and_story(text)
    if phase == "done":
        return "go", ""
    if phase != "waiting-review":
        return "stop", "Story " + story + " is unfinished. Run /resume-story."
    if pr_state is None:
        raise UsageError("the story is waiting for review: give --pr-state (open, merged or closed)")
    value = pr_state.lower()
    if value == "merged":
        return "mark-done", ""
    if value in ("open", "opened"):
        return "stop", "Story " + story + " is still waiting for your review. Merge it first."
    if value == "closed":
        return "stop", "Story " + story + "'s PR was closed without being merged. Look at it first."
    raise UsageError("--pr-state must be open, merged or closed (got " + repr(pr_state) + ")")


def wip_message(text: str, branch: str, task: Optional[str] = None) -> str:
    """The commit message for interrupted work: `t-3: [wip] interrupted, not reviewed`, or
    `story-2: ...` when no task was in progress. Raises RefusedError when `branch` is not the story
    branch or no story is running, UsageError for a task that is not in the table."""
    phase, story = _phase_and_story(text)
    story_branch = header_value(text, "story_branch")
    if not story_branch:
        raise DataError("the state file has no story_branch: line")
    if phase == "done":
        raise RefusedError("there is no story in progress (phase is done)")
    if story_branch == "none":
        raise RefusedError("the story branch is not created yet: there is nothing to commit to")
    if branch != story_branch:
        raise RefusedError(
            "you are on " + branch + ", not on the story branch " + story_branch
            + ": do not commit anywhere else"
        )
    prefix = "story-" + story
    if task is not None:
        if not schema.TASK_ID.fullmatch(task):
            raise UsageError("task must look like t-3 (got " + repr(task) + ")")
        if task not in [row["id"] for row in read_tasks(text)]:
            raise UsageError("unknown task: " + task)
        prefix = task
    return prefix + ": [wip] interrupted, not reviewed"


_FACT_BOOLS = ("feature_branch_exists", "story_branch_exists", "feature_moved", "cli_logged_in")
_FACT_LISTS = ("unknown_commits", "tree_dirty", "config_problems", "state_problems")
_FACT_KEYS = _FACT_BOOLS + _FACT_LISTS + ("current_branch", "task_commits", "issues", "pr")
_ISSUE_STATES = ("open", "closed", "missing")
_PR_FACTS = ("open", "merged", "closed", "missing")
_COMMITTED = ("tests-red", "green", "in-review", "done")


def parse_facts(text: str) -> Dict[str, Any]:
    """Read and validate the facts JSON for `reconcile`. Raises UsageError for anything wrong."""
    try:
        facts = json.loads(text)
    except ValueError as err:
        raise UsageError("the facts are not valid JSON: " + str(err)) from None
    if not isinstance(facts, dict):
        raise UsageError("the facts must be a JSON object")
    for key, value in facts.items():
        if key not in _FACT_KEYS:
            raise UsageError("unknown fact: " + key)
        if key in _FACT_BOOLS and not isinstance(value, bool):
            raise UsageError(key + " must be true or false")
        if key == "current_branch" and not isinstance(value, str):
            raise UsageError(key + " must be text")
        if key in _FACT_LISTS:
            if not isinstance(value, list):
                raise UsageError(key + " must be a list")
            if not all(isinstance(item, str) for item in value):
                raise UsageError(key + " must hold text")
        if key == "pr" and value not in _PR_FACTS:
            raise UsageError("pr must be open, merged, closed or missing")
        if key == "task_commits":
            if not isinstance(value, dict):
                raise UsageError("task_commits must be an object")
            for task_id, has in value.items():
                if not schema.TASK_ID.fullmatch(task_id):
                    raise UsageError("task_commits: " + repr(task_id) + " is not a task id like t-3")
                if not isinstance(has, bool):
                    raise UsageError("task_commits." + task_id + " must be true or false")
        if key == "issues":
            if not isinstance(value, dict):
                raise UsageError("issues must be an object")
            for name, state in value.items():
                if name != "story" and not schema.TASK_ID.fullmatch(name):
                    raise UsageError("issues: " + repr(name) + " must be story or a task id like t-3")
                if state not in _ISSUE_STATES:
                    raise UsageError("issues." + name + " must be open, closed or missing")
    return facts


def reconcile(text: str, facts: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Compare the state file with the facts gathered from git, the tracker and the PR. Returns
    (kind, message) pairs: `risky` ones first, then `harmless` ones that can be adopted."""
    keys = ("phase", "feature_branch", "story_branch", "pr", "story_issue")
    values = {key: header_value(text, key) for key in keys}
    for key, value in values.items():
        if value is None:
            raise DataError("the state file has no " + key + ": line")
    phase, feature = str(values["phase"]), str(values["feature_branch"])
    story_branch, pr, story_issue = str(values["story_branch"]), str(values["pr"]), str(values["story_issue"])
    tasks = read_tasks(text)
    risky: List[str] = []
    harmless: List[str] = []

    if facts.get("feature_branch_exists") is False:
        risky.append("the feature branch " + feature + " does not exist")
    has_story_branch = story_branch != "none"
    if has_story_branch and facts.get("story_branch_exists") is False:
        risky.append("the story branch " + story_branch + " does not exist")
    if facts.get("feature_moved") is True:
        risky.append("the feature branch moved since the story branch was created")

    status = {row["id"]: row["status"] for row in tasks}
    for task_id, has_commits in facts.get("task_commits", {}).items():
        if has_commits is False and status.get(task_id) in _COMMITTED:
            risky.append(task_id + " is " + status[task_id] + " in the state but has no commits on the story branch")

    unknown = facts.get("unknown_commits", [])
    if unknown:
        harmless.append(
            str(len(unknown)) + (" commit" if len(unknown) == 1 else " commits")
            + " on the story branch that the state does not know about (" + "; ".join(unknown)
            + "): the developer's own work, adopt it and journal an EDIT line"
        )

    current = facts.get("current_branch")
    dirty = [line.strip() for line in facts.get("tree_dirty", [])]
    off_branch = has_story_branch and current is not None and current != story_branch
    if dirty and off_branch:
        risky.append(
            "the working tree has uncommitted changes (" + ", ".join(dirty) + ") and you are on " + str(current)
            + ", not on the story branch " + story_branch + ": do not commit them"
        )
    elif dirty:
        harmless.append("uncommitted changes (" + ", ".join(dirty) + "): commit them as a WIP commit")
    elif off_branch:
        harmless.append("you are on " + str(current) + ", not on the story branch " + story_branch)

    issues = facts.get("issues", {})
    if story_issue != "none" and issues.get("story") in ("closed", "missing"):
        risky.append("the story issue (#" + story_issue + ") is " + issues["story"])
    for row in tasks:
        if row["issue"] != "none" and issues.get(row["id"]) in ("closed", "missing"):
            risky.append(row["id"] + "'s issue (#" + row["issue"] + ") is " + issues[row["id"]])

    pr_fact = facts.get("pr")
    if pr != "none" and pr_fact is not None:
        if pr_fact == "merged" and phase == "waiting-review":
            harmless.append("PR " + pr + " is merged: the story is finished, set the phase to done")
        elif pr_fact in ("merged", "closed", "missing"):
            risky.append("PR " + pr + " is " + pr_fact)

    if facts.get("cli_logged_in") is False:
        risky.append("the tracker CLI is not logged in")
    risky += ["config: " + problem for problem in facts.get("config_problems", [])]
    risky += ["state: " + problem for problem in facts.get("state_problems", [])]
    return [("risky", message) for message in risky] + [("harmless", message) for message in harmless]


def read_tasks(text: str) -> List[Dict[str, str]]:
    """The rows of the task table, each as a dict keyed by column name. Raises DataError when the
    file has no task table."""
    lines = _split(text)
    rows = _table_lines(lines)[2:]
    return [
        dict(zip(schema.TASK_COLUMNS, [cell.strip() for cell in lines[index].split("|")[1:-1]]))
        for index in rows
    ]


def read_flags(text: str) -> List[str]:
    """The lines of the Flags section that start with `- `, exactly as written."""
    return [line for _index, line in _flags(_split(text))[2]]


def add_flag(text: str, task_id: str, reason: str) -> str:
    """Append `- <task>: <reason>` to the Flags section. Raises UsageError for an unknown task or a
    bad reason, RefusedError when the task is already flagged, DataError without a Flags section."""
    problem = schema.FLAG_REASON_RULE(reason)
    if problem:
        raise UsageError(problem)
    lines = _split(text)
    _find_row(_require_table(lines), task_id)
    start, end, existing = _flags(lines)
    if start is None:
        raise DataError("the file has no " + schema.FLAGS_HEADING + " section")
    for _index, line in existing:
        match = schema.FLAG_LINE.fullmatch(line)
        if match and match.group(1) == task_id:
            raise RefusedError(task_id + " is already flagged")
    position = end
    while position - 1 > start and not lines[position - 1].strip():
        position -= 1
    lines.insert(position, "- " + task_id + ": " + reason)
    return _join(lines)


def set_task(text: str, task_id: str, field: str, value: str) -> str:
    """Set one cell in a task row. Same errors as set_header."""
    if field in schema.TASK_COUNTER_FIELDS:
        raise RefusedError(field + " is a counter: use bump, not set")
    if field not in schema.SETTABLE_TASK_FIELDS:
        raise UsageError("cannot set " + field + " (settable: " + " ".join(schema.SETTABLE_TASK_FIELDS) + ")")
    problem = schema.TASK_RULES[field](value)
    if problem:
        raise UsageError(problem)
    lines = _split(text)
    row = _find_row(_require_table(lines), task_id)
    lines[row.line] = _with_cell(row, schema.TASK_COLUMNS.index(field), value)
    return _join(lines)


def _parse_counter(label: str, value: str) -> Tuple[int, int]:
    match = schema.COUNTER.fullmatch(value.strip())
    if not match:
        raise DataError(label + ' "' + value.strip() + '" is not used/cap, like 1/3')
    return int(match.group(1)), int(match.group(2))


def bump(text: str, key: str, task_id: Optional[str] = None) -> Tuple[str, str, str]:
    """Increase one counter by one. Returns (new text, old value, new value).
    Raises RefusedError at the cap, UsageError for a non-counter, DataError for a bad counter."""
    lines = _split(text)
    if task_id is None:
        if key in schema.TASK_COUNTER_FIELDS:
            raise UsageError(key + " is a task counter: give --task")
        if key not in schema.COUNTER_KEYS:
            raise UsageError(key + " is not a counter")
        where = _header_lines(lines).get(key)
        if not where:
            raise DataError("the file has no " + key + ": line")
        label = key
        old = _header_value(lines, where[0]).strip()
        used, cap = _parse_counter(label, old)
        new = _bumped(label, old, used, cap)
        lines[where[0]] = key + ": " + new
        return _join(lines), old, new
    if key not in schema.TASK_COUNTER_FIELDS:
        raise UsageError(key + " is not a counter")
    row = _find_row(_require_table(lines), task_id)
    column = schema.TASK_COLUMNS.index(key)
    label = task_id + " " + key
    old = row.cells[column].strip()
    used, cap = _parse_counter(label, old)
    new = _bumped(label, old, used, cap)
    lines[row.line] = _with_cell(row, column, new)
    return _join(lines), old, new


def _bumped(label: str, old: str, used: int, cap: int) -> str:
    if used >= cap:
        raise RefusedError(label + " is at cap (" + old + ")")
    return str(used + 1) + "/" + str(cap)


def _problem(label: str, value: str, rule: str) -> str:
    return label + ' "' + value + '" is not valid: ' + rule


def _check_counter(label: str, value: str) -> Optional[str]:
    match = schema.COUNTER.fullmatch(value)
    if not match:
        return _problem(label, value, "expected used/cap, like 1/3")
    if int(match.group(1)) > int(match.group(2)):
        return label + ' "' + value + '" is over its cap'
    return None


def check(text: str) -> List[str]:
    """Return every problem found, one message per problem. Empty list means valid."""
    problems: List[str] = []
    lines = _split(text)

    if not lines or lines[0] != schema.TITLE_LINE:
        problems.append('first line must be "' + schema.TITLE_LINE + '"')

    found = _header_lines(lines)
    allowed = schema.HEADER_KEYS
    for key in schema.HEADER_KEYS:
        if key not in found:
            problems.append("missing key: " + key)
    for key, where in found.items():
        if key not in allowed:
            problems.append("unknown key: " + key)
            continue
        if len(where) > 1:
            problems.append("key " + key + " appears twice")
        value = _header_value(lines, where[0])
        if key in schema.COUNTER_KEYS:
            problem = _check_counter(key, value)
            if problem:
                problems.append(problem)
            continue
        rule = schema.HEADER_RULES[key](value)
        if rule:
            problems.append(_problem(key, value, rule))

    header, rows = _table(lines)
    if header is None:
        problems.append("missing section: " + schema.TASKS_HEADING)
        return problems
    if tuple(header) != schema.TASK_COLUMNS:
        problems.append("task table header must be: | " + " | ".join(schema.TASK_COLUMNS) + " |")
    problems.extend(_check_rows(rows))
    problems.extend(_check_flags(lines, rows))
    return problems


def _check_flags(lines: List[str], rows: List[_Row]) -> List[str]:
    """Every flag line belongs to one flagged task, and every flagged task has one flag line."""
    problems: List[str] = []
    status = {
        row.cells[0].strip(): row.cells[schema.TASK_COLUMNS.index("status")].strip()
        for row in rows
        if len(row.cells) == len(schema.TASK_COLUMNS)
    }
    flagged_in_text: List[str] = []
    _start, _end, existing = _flags(lines)
    for _index, line in existing:
        match = schema.FLAG_LINE.fullmatch(line)
        if not match:
            problems.append('flag line "' + line + '" is not valid: expected - t-N: reason')
            continue
        task_id = match.group(1)
        if task_id in flagged_in_text:
            problems.append("flag for " + task_id + " appears twice")
            continue
        flagged_in_text.append(task_id)
        if task_id not in status:
            problems.append("flag for " + task_id + ": task does not exist")
        elif status[task_id] != "flagged":
            problems.append("flag for " + task_id + ": task is not flagged")
    for task_id, value in status.items():
        if value == "flagged" and task_id not in flagged_in_text:
            problems.append(task_id + " is flagged but has no flag line")
    return problems


def _check_rows(rows: List[_Row]) -> List[str]:
    problems: List[str] = []
    width = len(schema.TASK_COLUMNS)
    good = [row for row in rows if len(row.cells) == width]
    for row in rows:
        if len(row.cells) != width:
            problems.append("task row " + row.cells[0].strip() + " has " + str(len(row.cells)) + " cells, expected " + str(width))

    ids = [row.cells[0].strip() for row in good]
    for task_id in ids:
        if not schema.TASK_ID.fullmatch(task_id):
            problems.append('task id "' + task_id + '" is not valid: expected t-1, t-2, ...')
    seen = set()
    for task_id in ids:
        if task_id in seen:
            problems.append("task id " + task_id + " appears twice")
        seen.add(task_id)

    known = set(ids)
    for row in good:
        task_id = row.cells[0].strip()
        value = {name: row.cells[i].strip() for i, name in enumerate(schema.TASK_COLUMNS)}
        for field in schema.SETTABLE_TASK_FIELDS:
            rule = schema.TASK_RULES[field](value[field])
            if rule:
                problems.append(_problem(task_id + " " + field, value[field], rule))
        for field in schema.TASK_COUNTER_FIELDS:
            problem = _check_counter(task_id + " " + field, value[field])
            if problem:
                problems.append(problem)
        if schema.TASK_RULES["blocked_by"](value["blocked_by"]) is None and value["blocked_by"] != "none":
            for blocker in value["blocked_by"].split(","):
                label = task_id + ' blocked_by "' + blocker + '"'
                if blocker == task_id:
                    problems.append(label + " is itself")
                elif blocker not in known:
                    problems.append(label + " does not exist")
    return problems
