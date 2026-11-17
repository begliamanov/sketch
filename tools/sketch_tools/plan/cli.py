"""Command-line layer of the plan tool: reads the files it is pointed at, prints the answer."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import UsageError
from sketch_tools.plan import logic


def _read(path_text: str) -> str:
    path = Path(path_text)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise UsageError("cannot read " + str(path) + ": " + str(err.strerror)) from err


def _ids(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _report(problems: List[str], env: Env) -> int:
    if not problems:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    return exitcodes.CHECK_FAILED


def _configure_tasks_check(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tasks", required=True, metavar="PATH", help="the tasks file")
    parser.add_argument("--min-tasks", type=int, default=logic.DEFAULT_MIN_TASKS, metavar="N",
                        help="fewest tasks in a story (default %(default)s)")
    parser.add_argument("--max-tasks", type=int, default=logic.DEFAULT_MAX_TASKS, metavar="N",
                        help="most tasks in a story (default %(default)s)")


def _run_tasks_check(args: argparse.Namespace, env: Env) -> int:
    return _report(logic.check_tasks(_read(args.tasks), args.min_tasks, args.max_tasks), env)


def _configure_tasks_order(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tasks", required=True, metavar="PATH", help="the tasks file")
    parser.add_argument("--flagged", default="", metavar="IDS", help="flagged tasks, like t-2,t-4")
    parser.add_argument("--done", default="", metavar="IDS", help="finished tasks, like t-1,t-3")


def _run_tasks_order(args: argparse.Namespace, env: Env) -> int:
    for line in logic.order_tasks(_read(args.tasks), _ids(args.flagged), _ids(args.done)):
        env.stdout.write(line + "\n")
    return exitcodes.OK


def _configure_config_check(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, metavar="PATH", help="the config file")


def _run_config_check(args: argparse.Namespace, env: Env) -> int:
    return _report(logic.check_config(_read(args.config), os.path.isfile), env)


def build_tool() -> Tool:
    tool = Tool("plan", "Checks on the planning files and the order tasks run in.")
    tool.add_command(
        "tasks-check", "report every problem in a tasks file", _configure_tasks_check, _run_tasks_check
    )
    tool.add_command(
        "tasks-order", "print the run order: `run t-N` lines, then `skip t-N (blocked by ...)` lines",
        _configure_tasks_order, _run_tasks_order,
    )
    tool.add_command(
        "config-check", "report every problem in a config file, including skill files that are missing",
        _configure_config_check, _run_config_check,
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
