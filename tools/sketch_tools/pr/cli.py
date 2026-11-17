"""Command-line layer of the pr tool: reads the files it is pointed at and piped text."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import UsageError
from sketch_tools.pr import logic


def _read(path_text: str) -> str:
    path = Path(path_text)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise UsageError("cannot read " + str(path) + ": " + str(err.strerror)) from err


def _report(problems: List[str], env: Env) -> int:
    if not problems:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    return exitcodes.CHECK_FAILED


def _configure_render_body(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", required=True, metavar="PATH", help="the state file")
    parser.add_argument("--extras", required=True, metavar="PATH",
                        help="JSON: summary, tests_passed, reviewer_model, and optional unresolved, "
                             "nice_to_have, manual_checks, differs, wip_commits")
    parser.add_argument("--max-lines", type=int, default=logic.DEFAULT_MAX_LINES, metavar="N",
                        help="line limit of the description, flags and the fold not counted (default %(default)s)")


def _run_render_body(args: argparse.Namespace, env: Env) -> int:
    extras = logic.parse_extras(_read(args.extras))
    env.stdout.write(logic.render_body(_read(args.state), extras, args.max_lines))
    return exitcodes.OK


def _configure_check_base(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base", required=True, metavar="BRANCH", help="the branch the PR must target")
    parser.add_argument("--head", metavar="BRANCH", help="the branch the PR must come from")


def _run_check_base(args: argparse.Namespace, env: Env) -> int:
    return _report(logic.check_base(env.stdin.read(), args.base, args.head), env)


def _configure_check_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", required=True, metavar="PATH", help="the state file")
    parser.add_argument("--extras", metavar="PATH", help="the extras file, to check unresolved items too")


def _run_check_flags(args: argparse.Namespace, env: Env) -> int:
    extras = logic.parse_extras(_read(args.extras)) if args.extras else None
    return _report(logic.check_flags(env.stdin.read(), _read(args.state), extras), env)


def build_tool() -> Tool:
    tool = Tool("pr", "The story PR: build its description, check it after it is opened.")
    tool.add_command(
        "render-body", "print the PR description built from the state file and the extras file",
        _configure_render_body, _run_render_body,
    )
    tool.add_command(
        "check-base", "stdin: `gh pr view --json baseRefName,headRefName,state` (or the glab JSON). "
        "The base must be the feature branch.", _configure_check_base, _run_check_base,
    )
    tool.add_command(
        "check-flags", "stdin: the PR description. Every flag and unresolved item must be in it.",
        _configure_check_flags, _run_check_flags,
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
