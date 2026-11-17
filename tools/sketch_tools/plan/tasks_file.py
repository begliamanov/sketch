"""Read `tasks.md` into plain parts. It only splits the text; deciding what is wrong is logic.py's
job. Format: core/agents/task-writer.md."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

FIRST_LINE = re.compile(r"# Tasks for story (\d+): \S.*")
TABLE_COLUMNS = ("id", "title", "blocked_by", "scenarios")
LABELS = ("Blocked by", "Delivers", "Acceptance criteria", "Test scenarios", "Terms", "Out of scope")
_LABEL = re.compile(r"(" + "|".join(LABELS) + r"):[ ]*(.*)")
_HEADING = re.compile(r"## (\S+): (.*)")
_CRITERION = re.compile(r"(\d+)\. (.*)")


@dataclass
class Block:
    """One `## t-N: title` section."""

    task_id: str
    title: str
    labels: Dict[str, str] = field(default_factory=dict)
    label_counts: Dict[str, int] = field(default_factory=dict)
    criteria: List[Tuple[int, str]] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)


@dataclass
class TasksFile:
    first_line_ok: bool
    table_header: Optional[List[str]]  # stripped cells of the header line, None without a table
    rows: List[List[str]]  # stripped cells of each data row
    blocks: List[Block]


def _cells(line: str) -> List[str]:
    return [cell.strip() for cell in line.split("|")[1:-1]]


def parse_tasks(text: str) -> TasksFile:
    lines = text.split("\n")
    first = next((line for line in lines if line.strip()), "")
    first_heading = next((i for i, line in enumerate(lines) if _HEADING.fullmatch(line)), len(lines))

    # the table sits above the first block: a header line, a separator line, then the rows
    head = lines[:first_heading]
    table_header: Optional[List[str]] = None
    rows: List[List[str]] = []
    start = next((i for i, line in enumerate(head) if line.startswith("|")), None)
    if start is not None:
        table_header = _cells(head[start])
        position = start + 2
        while position < len(head) and head[position].startswith("|"):
            rows.append(_cells(head[position]))
            position += 1

    blocks: List[Block] = []
    current: Optional[Block] = None
    section: Optional[str] = None
    for line in lines[first_heading:]:
        heading = _HEADING.fullmatch(line)
        if heading:
            current = Block(heading.group(1), heading.group(2).strip())
            blocks.append(current)
            section = None
            continue
        if current is None:
            continue
        label = _LABEL.fullmatch(line)
        if label:
            name, value = label.group(1), label.group(2).strip()
            current.label_counts[name] = current.label_counts.get(name, 0) + 1
            current.labels.setdefault(name, value)
            section = name
        elif section == "Acceptance criteria":
            criterion = _CRITERION.fullmatch(line)
            if criterion:
                current.criteria.append((int(criterion.group(1)), criterion.group(2).strip()))
        elif section == "Test scenarios" and line.startswith("- "):
            current.scenarios.append(line[2:].strip())

    return TasksFile(bool(FIRST_LINE.fullmatch(first)), table_header, rows, blocks)
