"""Pure plan logic: check `tasks.md` and `config.md`, and work out the run order. No file access
(the config check is given a function that says whether a skill file exists)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.core import config_file
from sketch_tools.plan import tasks_file
from sketch_tools.plan.graph import find_cycle, task_number
from sketch_tools.tests.readers import BUILTIN_NAMES
from sketch_tools.tests.settings import TARGET_PLACEHOLDER, results_pattern_problem

DEFAULT_MIN_TASKS = 3
DEFAULT_MAX_TASKS = 8

_ID = re.compile(r"t-\d+")
_BLOCKED = re.compile(r"none|t-\d+(?:\s*,\s*t-\d+)*")
_NOT_EMPTY_LABELS = ("Blocked by", "Delivers", "Terms", "Out of scope")


@dataclass
class _Task:
    task_id: str
    title: str
    blockers: List[str]
    scenarios: str


def _blockers(value: str) -> List[str]:
    return [] if value.strip() == "none" else [part.strip() for part in value.split(",")]


def _table(parsed: tasks_file.TasksFile) -> Tuple[List[str], List[_Task]]:
    """Problems with the task table (header, rows, blockers, cycles) and its valid rows."""
    if parsed.table_header is None:
        return ["missing task table: | id | title | blocked_by | scenarios |"], []
    problems: List[str] = []
    if tuple(parsed.table_header) != tasks_file.TABLE_COLUMNS:
        problems.append("table header must be: | " + " | ".join(tasks_file.TABLE_COLUMNS) + " |")
    tasks: List[_Task] = []
    seen: Set[str] = set()
    width = len(tasks_file.TABLE_COLUMNS)
    for cells in parsed.rows:
        if len(cells) != width:
            label = cells[0] if cells else "?"
            problems.append("table row " + label + " has " + str(len(cells)) + " cells, expected " + str(width))
            continue
        task_id, title, blocked, scenarios = cells
        if not _ID.fullmatch(task_id):
            problems.append('task id "' + task_id + '" is not valid: expected t-1, t-2, ...')
            continue
        if task_id in seen:
            problems.append("task id " + task_id + " appears twice")
            continue
        seen.add(task_id)
        if not scenarios.isdigit():
            problems.append(task_id + ' scenarios "' + scenarios + '" is not a number')
        blockers: List[str] = []
        if _BLOCKED.fullmatch(blocked):
            blockers = _blockers(blocked)
        else:
            problems.append(task_id + ' blocked_by "' + blocked + '" is not valid: expected none or ids like t-1, t-2')
        tasks.append(_Task(task_id, title, blockers, scenarios))

    for task in tasks:
        for blocker in task.blockers:
            label = task.task_id + ' blocked_by "' + blocker + '"'
            if blocker == task.task_id:
                problems.append(label + " is itself")
            elif blocker not in seen:
                problems.append(label + " does not exist")
    cycle = find_cycle({t.task_id: [b for b in t.blockers if b != t.task_id] for t in tasks})
    if cycle:
        problems.append("dependency cycle: " + " -> ".join(cycle))
    return problems, tasks


def _plural(count: int, word: str) -> str:
    return str(count) + " " + word + ("" if count == 1 else "s")


def _check_block(block: tasks_file.Block, by_id: Dict[str, _Task]) -> List[str]:
    task_id = block.task_id
    problems: List[str] = []
    for label in tasks_file.LABELS:
        count = block.label_counts.get(label, 0)
        if count == 0:
            problems.append(task_id + ' is missing "' + label + ':"')
        elif count > 1:
            problems.append(task_id + ' has "' + label + ':" twice')
    for label in _NOT_EMPTY_LABELS:
        if block.label_counts.get(label) and not block.labels.get(label):
            problems.append(task_id + ' has an empty "' + label + ':"')

    has_criteria_label = "Acceptance criteria" in block.labels
    if has_criteria_label and not block.criteria:
        problems.append(task_id + " has no acceptance criteria")
    numbers = [number for number, _text in block.criteria]
    if block.criteria and numbers != list(range(1, len(numbers) + 1)):
        problems.append(
            task_id + " acceptance criteria must be numbered 1, 2, 3, ... (found "
            + ", ".join(str(n) for n in numbers) + ")"
        )
    if "Test scenarios" in block.labels and not block.scenarios:
        problems.append(task_id + " has no test scenarios")
    if block.criteria and block.scenarios and len(block.scenarios) < len(block.criteria):
        problems.append(
            task_id + " has " + str(len(block.criteria)) + " criteria but only "
            + _plural(len(block.scenarios), "scenario")
            + ": every criterion needs at least one"
        )

    task = by_id.get(task_id)
    if task is None:
        return problems
    if block.title != task.title:
        problems.append(task_id + ' title differs: table "' + task.title + '", block "' + block.title + '"')
    blocked_text = block.labels.get("Blocked by")
    if blocked_text and _BLOCKED.fullmatch(blocked_text) and _blockers(blocked_text) != task.blockers:
        problems.append(
            task_id + ' blocked_by differs: table "' + (", ".join(task.blockers) or "none")
            + '", block "' + blocked_text + '"'
        )
    if task.scenarios.isdigit() and int(task.scenarios) != len(block.scenarios):
        problems.append(
            task_id + " table says " + _plural(int(task.scenarios), "scenario")
            + ", block lists " + str(len(block.scenarios))
        )
    return problems


def check_tasks(
    text: str, min_tasks: int = DEFAULT_MIN_TASKS, max_tasks: int = DEFAULT_MAX_TASKS
) -> List[str]:
    """Every problem in a tasks.md, one message each. Empty list means valid."""
    parsed = tasks_file.parse_tasks(text)
    problems: List[str] = []
    if not parsed.first_line_ok:
        problems.append('first line must be "# Tasks for story <n>: <title>"')
    table_problems, tasks = _table(parsed)
    problems.extend(table_problems)
    by_id = {task.task_id: task for task in tasks}

    seen: Set[str] = set()
    for block in parsed.blocks:
        if not _ID.fullmatch(block.task_id):
            problems.append('block id "' + block.task_id + '" is not valid: expected t-1, t-2, ...')
            continue
        if block.task_id in seen:
            problems.append("block " + block.task_id + " appears twice")
            continue
        seen.add(block.task_id)
        if parsed.table_header is not None and block.task_id not in by_id:
            problems.append(block.task_id + " has a block but no row in the table")
        problems.extend(_check_block(block, by_id))
    for task in tasks:
        if task.task_id not in seen:
            problems.append(task.task_id + ' is in the table but has no block ("## ' + task.task_id + ': ...")')

    if parsed.table_header is not None:
        count = len(tasks)
        if count < min_tasks:
            problems.append(
                _plural(count, "task") + " is too few: a story needs at least " + str(min_tasks)
                + "; if it is this small, merge it into the next story"
            )
        elif count > max_tasks:
            problems.append(
                _plural(count, "task") + " is too many: a story can have at most " + str(max_tasks)
                + "; split the story"
            )
    return problems


def order_tasks(text: str, flagged: Sequence[str] = (), done: Sequence[str] = ()) -> List[str]:
    """The run order from the table's blocked_by: `run t-N` lines in order, then `skip t-N (blocked
    by ...)` lines for tasks that cannot run because a blocker is flagged or skipped. Tasks in
    `done` are satisfied blockers and are not run again. Raises DataError for a damaged table or a
    cycle, UsageError for an id that is not in the table."""
    problems, tasks = _table(tasks_file.parse_tasks(text))
    if problems:
        cycles = [p for p in problems if "cycle" in p]
        raise DataError(cycles[0] if cycles else "; ".join(problems[:3]))
    deps = {task.task_id: task.blockers for task in tasks}
    for name, values in (("flagged", flagged), ("done", done)):
        for value in values:
            if value not in deps:
                raise UsageError(name + " task " + value + " is not in the table")
    both = set(flagged) & set(done)
    if both:
        raise UsageError(sorted(both, key=task_number)[0] + " cannot be both done and flagged")

    ids = sorted(deps, key=task_number)
    blocking: Set[str] = set(flagged)  # flagged, or skipped because of a flagged task
    skipped: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for task_id in ids:
            if task_id in blocking or task_id in done:
                continue
            if any(blocker in blocking for blocker in deps[task_id]):
                blocking.add(task_id)
                skipped.add(task_id)
                changed = True

    placed: Set[str] = set(done)
    remaining = [t for t in ids if t not in blocking and t not in done]
    lines: List[str] = []
    while remaining:
        ready = [t for t in remaining if all(b in placed for b in deps[t])]
        if not ready:  # cannot happen without a cycle, which was ruled out above
            raise DataError("dependency cycle among: " + ", ".join(remaining))
        chosen = ready[0]  # remaining is already in task-number order
        lines.append("run " + chosen)
        placed.add(chosen)
        remaining.remove(chosen)
    for task_id in sorted(skipped, key=task_number):
        causes = sorted((b for b in deps[task_id] if b in blocking), key=task_number)
        lines.append("skip " + task_id + " (blocked by " + ", ".join(causes) + ")")
    return lines


_TRACKERS = {"github": "gh", "gitlab": "glab"}
_REQUIRED_KEYS = ("tracker", "tracker_cli", "default_branch", "test_full", "test_task", "test_paths",
                  "test_format", "test_results")
_OPTIONAL_KEYS = ("formats_dir",)
_ROLES = ("common", "task-writer", "test-writer", "implementer", "reviewer", "story-reviewer")


def _check_keys(config: config_file.ConfigFile, formats: Sequence[str]) -> List[str]:
    problems: List[str] = []
    for key in _REQUIRED_KEYS:
        if key not in config.keys:
            problems.append("missing key: " + key)
    for key, count in config.key_counts.items():
        if key not in _REQUIRED_KEYS and key not in _OPTIONAL_KEYS:
            problems.append("unknown key: " + key)
        elif count > 1:
            problems.append("key " + key + " appears twice")

    tracker = config.keys.get("tracker")
    cli = config.keys.get("tracker_cli")
    if tracker is not None and tracker not in _TRACKERS:
        problems.append('tracker "' + tracker + '" is not valid: must be github or gitlab')
    if cli is not None and cli not in _TRACKERS.values():
        problems.append('tracker_cli "' + cli + '" is not valid: must be gh or glab')
    if tracker in _TRACKERS and cli in _TRACKERS.values() and _TRACKERS[tracker] != cli:
        problems.append(
            'tracker_cli "' + cli + '" does not match tracker "' + tracker
            + '" (expected ' + _TRACKERS[tracker] + ")"
        )
    branch = config.keys.get("default_branch")
    if branch is not None and (not branch or re.search(r"\s", branch)):
        problems.append("default_branch must be one word, like main")
    if config.keys.get("test_full") == "":
        problems.append("test_full must not be empty")
    test_task = config.keys.get("test_task")
    if test_task is not None and TARGET_PLACEHOLDER not in test_task:
        problems.append("test_task must contain the placeholder " + TARGET_PLACEHOLDER)
    test_format = config.keys.get("test_format")
    if test_format == "":
        problems.append("test_format must not be empty")
    elif test_format is not None and test_format not in formats:
        problems.append(
            'test_format "' + test_format + '" is not a format that can be read (known: ' + ", ".join(formats) + ")"
        )
    results = config.keys.get("test_results")
    if results is not None:
        pattern_problem = results_pattern_problem(results)
        if pattern_problem:
            problems.append("test_results: " + pattern_problem)
    if config.keys.get("formats_dir") == "":
        problems.append("formats_dir must not be empty when it is given")
    if "test_paths" in config.keys:
        items, problem = config_file.parse_list(config.keys["test_paths"])
        if items is None:
            problems.append("test_paths must be a list like [Tests/**, src/test/**]")
        else:
            if problem:
                problems.append("test_paths has an empty item")
            if not items:
                problems.append("test_paths must have at least one glob")
    return problems


def _check_skills(config: config_file.ConfigFile, exists: Callable[[str], bool]) -> List[str]:
    if not config.has_skills:
        return ["missing section: skills:"]
    problems: List[str] = []
    for role in _ROLES:
        if role not in config.roles:
            problems.append("missing skills role: " + role)
    for role, count in config.role_counts.items():
        if role not in _ROLES:
            problems.append("unknown skills role: " + role)
        elif count > 1:
            problems.append("skills role " + role + " appears twice")
    for role in _ROLES:
        if role not in config.roles:
            continue
        paths, problem = config_file.parse_list(config.roles[role])
        if paths is None:
            problems.append("skills role " + role + " must be a list like [/path/to/SKILL.md]")
            continue
        if problem:
            problems.append("skills role " + role + " has an empty item")
        for path in paths:
            label = "skills role " + role + ': "' + path + '"'
            if not path.startswith("/"):
                problems.append(label + " is not an absolute path")
            elif not path.endswith("/SKILL.md"):
                problems.append(label + " is not a SKILL.md file")
            elif not exists(path):
                problems.append("skills role " + role + ": skill file does not exist: " + path)
    return problems


def check_config(
    text: str, exists: Callable[[str], bool], formats: Sequence[str] = BUILTIN_NAMES
) -> List[str]:
    """Every problem in a config.md, one message each. `exists` says whether a skill file exists;
    `formats` are the test result formats that can be read (the built-in ones, and the project's own)."""
    config = config_file.parse_config(text)
    problems: List[str] = []
    if not config.first_line_ok:
        problems.append('first line must be "' + config_file.FIRST_LINE + '"')
    problems.extend(_check_keys(config, formats))
    problems.extend(_check_skills(config, exists))
    for line in config.stray:
        problems.append("unexpected line: " + line.strip())
    return problems
