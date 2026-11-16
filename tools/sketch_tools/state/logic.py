"""Pure state logic: read, edit and check the text of state.md. No file access.

Edits are minimal: only the one line or table cell that changes is touched, so everything else
(order, alignment, the Flags section) stays byte for byte.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
    allowed = schema.HEADER_KEYS + schema.OPTIONAL_KEYS
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
