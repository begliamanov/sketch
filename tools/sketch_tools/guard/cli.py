"""Command-line layer of the guard tool: reads the hook input, answers by exit code.

Claude Code runs this before every Bash command. Exit 0 lets the command run, exit 2 blocks it and
shows stderr to the agent. It fails closed: input it cannot read, a command it cannot parse and a
bug in the guard itself all block. Its launcher goes one step further: any exit code other than 0
becomes 2 (a wrong option in the hook line, no python3), because Claude Code lets a command run on
every other failure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import RefusedError, ToolError
from sketch_tools.guard import logic
from sketch_tools.state.logic import header_value, read_tasks


def _configure_check_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--protect", action="append", default=[], metavar="BRANCH",
                        help="a branch nobody may push to, like main. Repeat for more.")
    parser.add_argument("--state", metavar="PATH",
                        help="the state file: its feature_branch is protected too. A missing file blocks every "
                             "issue close; one without a feature_branch blocks every push. Its task table says "
                             "which issues may be closed.")
    parser.add_argument("--raw", action="store_true",
                        help="stdin is the command itself, not the hook's JSON (for trying it out)")


def _command_from_hook(raw: str) -> Optional[str]:
    """The Bash command in the hook's JSON, or None for another tool. Refuses unreadable input."""
    try:
        data: Any = json.loads(raw)
    except ValueError:
        raise RefusedError("cannot read the hook input: it is not JSON") from None
    if not isinstance(data, dict):
        raise RefusedError("cannot read the hook input: expected a JSON object")
    if data.get("tool_name") != "Bash":
        return None
    tool_input = data.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        raise RefusedError("the Bash call has no command to check")
    return command


def _protection(args: argparse.Namespace) -> "tuple[List[str], Optional[str]]":
    """The protected branches, and a reason to refuse every push when the state is unusable."""
    protected = list(args.protect)
    if not args.state:
        return protected, None
    path = Path(args.state)
    if not path.exists():
        return protected, None
    try:
        feature = header_value(path.read_text(encoding="utf-8"), "feature_branch")
    except OSError as err:
        return protected, "cannot read " + str(path) + " (" + str(err.strerror) + "), so pushes cannot be checked"
    if not feature or feature == "none":
        return protected, str(path) + " has no feature_branch, so pushes cannot be checked: run state check"
    return protected + [feature], None


def _closable_issues(args: argparse.Namespace) -> "tuple[List[str], Optional[str]]":
    """The issue numbers of the current story's tasks, and a reason to refuse every close when the
    state file cannot say (not given, missing, unreadable, no task table)."""
    if not args.state:
        return [], "no state file is given, so closing an issue cannot be checked"
    path = Path(args.state)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], str(path) + " does not exist, so closing an issue cannot be checked"
    except OSError as err:
        return [], "cannot read " + str(path) + " (" + str(err.strerror) + "), so closing an issue cannot be checked"
    try:
        return [row["issue"] for row in read_tasks(text)], None
    except ToolError:
        return [], str(path) + " has no task table, so closing an issue cannot be checked"


def _run_check_command(args: argparse.Namespace, env: Env) -> int:
    raw = env.stdin.read()
    command = raw.strip("\n") if args.raw else _command_from_hook(raw)
    if command is None:
        return exitcodes.OK
    try:
        protected, push_block = _protection(args)
        task_issues, close_block = _closable_issues(args)
        reasons = logic.check_command(command, protected, push_block, task_issues, close_block)
    except ToolError:
        raise
    except Exception as err:  # a bug in the guard must never let a command through
        raise RefusedError(
            "the guard failed on this command (" + type(err).__name__ + ": " + str(err)
            + "), so it is blocked: tell the developer"
        ) from err
    if reasons:
        raise RefusedError("; ".join(reasons))
    return exitcodes.OK


def build_tool() -> Tool:
    tool = Tool("guard", "Blocks the commands agents must never run. Runs as a PreToolUse hook.")
    tool.add_command(
        "check-command", "read a Bash tool call (hook JSON) and block merges, force pushes, pushes to "
        "protected branches and issue closing", _configure_check_command, _run_check_command,
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
