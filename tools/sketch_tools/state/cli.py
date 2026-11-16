"""Command-line layer of the state tool: parses arguments and touches the state file."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import UsageError
from sketch_tools.core.files import atomic_write
from sketch_tools.state import logic


def _add_state_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", required=True, metavar="PATH", help="the state file")


def _read(args: argparse.Namespace) -> str:
    path = Path(args.state)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise UsageError("cannot read " + str(path) + ": " + str(err.strerror)) from err


def _write(args: argparse.Namespace, text: str) -> None:
    path = Path(args.state)
    try:
        atomic_write(path, text)
    except OSError as err:
        raise UsageError("cannot write " + str(path) + ": " + str(err.strerror)) from err


def _configure_set(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("key", metavar="KEY", help="a header key, or a task field with --task")
    parser.add_argument("value", metavar="VALUE")
    parser.add_argument("--task", metavar="ID", help="set a field of this task, like t-3")
    _add_state_option(parser)


def _run_set(args: argparse.Namespace, env: Env) -> int:
    text = _read(args)
    if args.task:
        _write(args, logic.set_task(text, args.task, args.key, args.value))
        env.stdout.write("ok: " + args.task + " " + args.key + " = " + args.value + "\n")
    else:
        _write(args, logic.set_header(text, args.key, args.value))
        env.stdout.write("ok: " + args.key + " = " + args.value + "\n")
    return exitcodes.OK


def _configure_bump(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("key", metavar="COUNTER", help="story_rounds, or attempts / review_rounds with --task")
    parser.add_argument("--task", metavar="ID", help="bump a counter of this task, like t-3")
    _add_state_option(parser)


def _run_bump(args: argparse.Namespace, env: Env) -> int:
    new_text, old, new = logic.bump(_read(args), args.key, args.task)
    _write(args, new_text)
    where = (args.task + " ") if args.task else ""
    env.stdout.write("ok: " + where + args.key + " " + old + " -> " + new + "\n")
    return exitcodes.OK


def _configure_flag_add(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("reason", metavar="REASON", help="why, one line, kept exactly")
    parser.add_argument("--task", required=True, metavar="ID", help="the task to flag, like t-4")
    _add_state_option(parser)


def _run_flag_add(args: argparse.Namespace, env: Env) -> int:
    _write(args, logic.add_flag(_read(args), args.task, args.reason))
    env.stdout.write("ok: flagged " + args.task + "\n")
    return exitcodes.OK


def _run_check(args: argparse.Namespace, env: Env) -> int:
    problems = logic.check(_read(args))
    if not problems:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    return exitcodes.CHECK_FAILED


def build_tool() -> Tool:
    tool = Tool("state", "The story state file: set a field, bump a counter, check the file.")
    tool.add_command("set", "set one field, rejecting values outside the schema", _configure_set, _run_set)
    tool.add_command("bump", "increase one counter, refusing to pass its cap", _configure_bump, _run_bump)
    tool.add_command(
        "flag add", "append a flag line for a task (set its status separately)",
        _configure_flag_add, _run_flag_add,
    )
    tool.add_command("check", "report every problem in the file", _add_state_option, _run_check)
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
