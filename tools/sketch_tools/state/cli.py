"""Command-line layer of the state tool: parses arguments and touches the state file."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import DataError, RefusedError, UsageError
from sketch_tools.core.files import atomic_write
from sketch_tools.state import logic, schema


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


def _configure_new_story(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--story", required=True, metavar="N", help="the story number")
    parser.add_argument("--title", required=True, metavar="TEXT")
    parser.add_argument("--feature-branch", required=True, metavar="NAME", help="the current branch")
    parser.add_argument("--extra-skills", default="none", metavar="PATHS",
                        help="skill paths the developer gave for this story (default: none)")
    parser.add_argument("--story-rounds-cap", type=int, default=schema.DEFAULT_STORY_ROUNDS_CAP,
                        metavar="N", help="cap of the story-end rounds (default %(default)s)")
    _add_state_option(parser)


def _run_new_story(args: argparse.Namespace, env: Env) -> int:
    text = logic.new_story(args.story, args.title, args.feature_branch, args.extra_skills,
                           args.story_rounds_cap)
    path = Path(args.state)
    if path.exists():
        phase = logic.header_value(_read(args), "phase")
        if phase is None:
            raise DataError("cannot read the phase of the existing " + str(path) + " (no phase line)")
        if phase != "done":
            raise RefusedError(
                str(path) + " holds a story in progress (phase: " + phase + "); finish it first"
            )
    _write(args, text)
    env.stdout.write("ok: story " + args.story + " started\n")
    return exitcodes.OK


def _configure_task_add(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", required=True, metavar="ID", help="the task id, like t-5")
    parser.add_argument("--title", required=True, metavar="TEXT")
    parser.add_argument("--blocked-by", default="none", metavar="IDS",
                        help="none, or ids like t-1,t-2 (default: none)")
    parser.add_argument("--issue", default="none", metavar="N", help="the issue number (default: none)")
    parser.add_argument("--attempts-cap", type=int, default=schema.DEFAULT_ATTEMPTS_CAP, metavar="N",
                        help="cap of the implement attempts (default %(default)s)")
    parser.add_argument("--review-rounds-cap", type=int, default=schema.DEFAULT_REVIEW_ROUNDS_CAP,
                        metavar="N", help="cap of the review rounds (default %(default)s)")
    _add_state_option(parser)


def _run_task_add(args: argparse.Namespace, env: Env) -> int:
    _write(args, logic.add_task(_read(args), args.id, args.title, args.blocked_by, args.issue,
                                args.attempts_cap, args.review_rounds_cap))
    env.stdout.write("ok: added " + args.id + "\n")
    return exitcodes.OK


def _configure_gate(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pr-state", metavar="STATE",
                        help="open, merged or closed: the story's PR, needed when the story waits for review")
    _add_state_option(parser)


def _run_gate(args: argparse.Namespace, env: Env) -> int:
    text = _read(args) if Path(args.state).exists() else None
    decision, message = logic.gate(text, args.pr_state)
    if decision == "stop":
        env.stdout.write("stop: " + message + "\n")
        return exitcodes.CHECK_FAILED
    env.stdout.write(decision + "\n")
    return exitcodes.OK


def _configure_wip_message(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--branch", required=True, metavar="NAME", help="the branch you are on")
    parser.add_argument("--task", metavar="ID",
                        help="the task that was in progress; leave out for a story-level commit")
    _add_state_option(parser)


def _run_wip_message(args: argparse.Namespace, env: Env) -> int:
    env.stdout.write(logic.wip_message(_read(args), args.branch, args.task) + "\n")
    return exitcodes.OK


def _run_reconcile(args: argparse.Namespace, env: Env) -> int:
    found = logic.reconcile(_read(args), logic.parse_facts(env.stdin.read()))
    if not found:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for kind, message in found:
        env.stdout.write(kind + ": " + message + "\n")
    return exitcodes.CHECK_FAILED if any(kind == "risky" for kind, _ in found) else exitcodes.OK


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
    tool.add_command(
        "task add", "append a pending row to the task table",
        _configure_task_add, _run_task_add,
    )
    tool.add_command(
        "new-story", "write the state file of a new story (refuses to replace an unfinished one)",
        _configure_new_story, _run_new_story,
    )
    tool.add_command(
        "gate", "can a new story start? prints go, mark-done or stop: <why>", _configure_gate, _run_gate
    )
    tool.add_command(
        "wip-message", "print the commit message for interrupted work; refuses off the story branch",
        _configure_wip_message, _run_wip_message,
    )
    tool.add_command(
        "reconcile", "stdin: facts as JSON from git, the tracker and the PR. Prints risky and harmless differences.",
        _add_state_option, _run_reconcile,
    )
    tool.add_command("check", "report every problem in the file", _add_state_option, _run_check)
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
