"""Command-line layer of the journal tool: parses arguments and touches the journal file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import UsageError
from sketch_tools.core.files import append_text
from sketch_tools.journal import logic
from sketch_tools.journal.logic import ENTRY_TYPES, format_entry

HEADER = "# Drift journal\n"


def _configure_add(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("type", metavar="TYPE", help="one of " + " ".join(ENTRY_TYPES))
    parser.add_argument("story", metavar="STORY", help="story, like S2")
    parser.add_argument("task", metavar="TASK", help="task like t-2, or - for the whole story")
    parser.add_argument("text", metavar="TEXT", help="the event, one line, kept exactly")
    parser.add_argument("--me", action="store_true", help="mark the text as the developer's own")
    parser.add_argument("--journal", required=True, metavar="PATH", help="the journal file")


def _run_add(args: argparse.Namespace, env: Env) -> int:
    path = Path(args.journal)
    line = format_entry(args.type, args.story, args.task, args.text, env.now(), me=args.me)
    if not path.parent.is_dir():
        raise UsageError("folder does not exist: " + str(path.parent))
    prefix = _prefix_for(path)
    try:
        append_text(path, prefix + line + "\n")
    except OSError as err:
        raise UsageError("cannot write " + str(path) + ": " + err.strerror) from err
    env.stdout.write("appended: " + line + "\n")
    return exitcodes.OK


def _add_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--journal", required=True, metavar="PATH", help="the journal file")
    parser.add_argument("--story", action="append", default=[], metavar="S",
                        help="only this story, like S2. Repeat for more.")
    parser.add_argument("--after", type=int, metavar="N", help="only stories after story number N")


def _read_journal(args: argparse.Namespace) -> str:
    path = Path(args.journal)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise UsageError("cannot read " + str(path) + ": " + str(err.strerror)) from err


def _run_me_lines(args: argparse.Namespace, env: Env) -> int:
    for line in logic.me_lines(_read_journal(args), args.story, args.after):
        env.stdout.write(line + "\n")
    return exitcodes.OK


def _configure_signals(parser: argparse.ArgumentParser) -> None:
    _add_filters(parser)
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of a line per type")


def _run_signals(args: argparse.Namespace, env: Env) -> int:
    counts = logic.signals(_read_journal(args), args.story, args.after)
    if args.json:
        env.stdout.write(json.dumps(counts) + "\n")
    else:
        for entry_type, count in counts.items():
            env.stdout.write(entry_type + " " + str(count) + "\n")
    return exitcodes.OK


def _prefix_for(path: Path) -> str:
    """What must come before the new line: the header for a new journal, a newline if needed."""
    if not path.exists() or path.stat().st_size == 0:
        return HEADER
    with open(str(path), "rb") as handle:
        handle.seek(-1, 2)
        return "" if handle.read(1) == b"\n" else "\n"


def build_tool() -> Tool:
    tool = Tool("journal", "The append-only drift journal. Never rewrites an earlier line.")
    tool.add_command("add", "append one validated line", _configure_add, _run_add)
    tool.add_command(
        "me-lines", "print every line the developer wrote ([me]), verbatim", _add_filters, _run_me_lines
    )
    tool.add_command(
        "signals", "count the entries of each type", _configure_signals, _run_signals
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
