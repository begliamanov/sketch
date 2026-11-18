"""Command-line layer of the plan tool: reads the files it is pointed at, prints the answer."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core import config_file
from sketch_tools.state.logic import header_value
from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.plan import briefing, issues, logic, tasks_file, tracker
from sketch_tools.tests.readers import BUILTIN_NAMES, load_plugins


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
    text = _read(args.config)
    formats = list(BUILTIN_NAMES)
    extra: List[str] = []
    folder = config_file.parse_config(text).keys.get("formats_dir")
    if folder:  # the project's own readers: their names are formats too
        try:
            formats += list(load_plugins(Path(folder)))
        except (DataError, UsageError) as err:
            extra.append("formats_dir: " + str(err))
    return _report(logic.check_config(text, os.path.isfile, formats) + extra, env)


def _configure_brief_skills(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, metavar="PATH", help="the config file")
    parser.add_argument("--role", required=True, metavar="ROLE", help="the agent role, like implementer")
    parser.add_argument("--state", metavar="PATH", help="the state file: its extra_skills are added")
    parser.add_argument("--tasks", metavar="PATH", help="the tasks file; with --task, the role's skills are narrowed "
                                                        "to the ones on that task's Skills line (if it has one)")
    parser.add_argument("--task", metavar="ID", help="the task id, like t-3 (needs --tasks)")


def _run_brief_skills(args: argparse.Namespace, env: Env) -> int:
    extra: List[str] = []
    if args.state:
        extra = briefing.parse_extra_skills(header_value(_read(args.state), "extra_skills") or "none")
    if bool(args.tasks) != bool(args.task):
        raise UsageError("--tasks and --task go together")
    picks = tasks_file.task_skill_picks(_read(args.tasks), args.task) if args.tasks else None
    paths, problems = briefing.brief_skills(_read(args.config), args.role, extra, os.path.isfile, picks)
    if problems:
        for problem in problems:
            env.stdout.write("error: " + problem + "\n")
        return exitcodes.CHECK_FAILED
    for path in paths:
        env.stdout.write(path + "\n")
    return exitcodes.OK


def _configure_issues_todo(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tasks", required=True, metavar="PATH", help="the tasks file")


def _run_issues_todo(args: argparse.Namespace, env: Env) -> int:
    facts = issues.parse_issue_facts(env.stdin.read())
    lines = issues.issues_todo(_read(args.tasks), facts)
    for line in lines:
        env.stdout.write(line + "\n")
    return exitcodes.OK


def _run_detect_tracker(args: argparse.Namespace, env: Env) -> int:
    kind, cli, host = tracker.detect_tracker(env.stdin.read())
    if kind is None:
        env.stdout.write("ask: " + host + " is not github.com or a GitLab host: ask the developer which tracker this is\n")
        return exitcodes.CHECK_FAILED
    env.stdout.write("tracker: " + kind + "\ntracker_cli: " + str(cli) + "\n")
    return exitcodes.OK


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
    tool.add_command(
        "brief-skills", "print the skill files an agent of this role must read, one path per line",
        _configure_brief_skills, _run_brief_skills,
    )
    tool.add_command(
        "issues-todo", "stdin: the issues already on the tracker, as JSON. Prints what is there and what is still to create.",
        _configure_issues_todo, _run_issues_todo,
    )
    tool.add_command(
        "detect-tracker", "stdin: the git remote URL. Prints the tracker and its CLI, or asks.",
        lambda parser: None, _run_detect_tracker,
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
