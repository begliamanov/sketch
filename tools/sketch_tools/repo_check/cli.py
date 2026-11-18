"""Command-line layer of the repo-check tool: reads piped text, prints the problems."""

from __future__ import annotations

import argparse
from typing import Callable, List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Handler, Tool
from sketch_tools.repo_check import logic


def _report(problems: List[str], env: Env) -> int:
    if not problems:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    return exitcodes.CHECK_FAILED


def _piped(check: Callable[[str, argparse.Namespace], List[str]]) -> Handler:
    """Turn a check on piped text into a command handler."""

    def handler(args: argparse.Namespace, env: Env) -> int:
        return _report(check(env.stdin.read(), args), env)

    return handler


def _configure_commit_prefix(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task", metavar="ID", help="require this exact prefix, like t-3")


def _configure_tests_unchanged(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tests", required=True, action="append", metavar="GLOB",
        help="a test file pattern, like 'Tests/**'. Repeat for more.",
    )


def _configure_changelog(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--issue", required=True, action="append", metavar="N",
                        help="the task's issue number; with --story, repeat for every issue of the story")
    parser.add_argument("--story", action="store_true", help="accept several lines, one per story issue")


def build_tool() -> Tool:
    tool = Tool("repo-check", "Rules about commits, tests, the changelog and the working tree, "
                              "checked on text piped in from git.")
    tool.add_command(
        "commit-prefix", "stdin: commit subjects (git log --format=%%s). Flag any without a task prefix.",
        _configure_commit_prefix,
        _piped(lambda text, args: logic.check_commit_prefix(text, args.task)),
    )
    tool.add_command(
        "tests-unchanged", "stdin: changed file names (git diff --name-only). Flag test files.",
        _configure_tests_unchanged,
        _piped(lambda text, args: logic.check_tests_unchanged(text, args.tests)),
    )
    tool.add_command(
        "changelog", "stdin: a full-context diff of CHANGELOG.md (git diff -U99999). One new entry.",
        _configure_changelog,
        _piped(lambda text, args: logic.check_changelog(
            text, args.issue[-1], story_issues=args.issue if args.story else None)),
    )
    tool.add_command(
        "tree-clean", "stdin: git status --porcelain. Flag every dirty or untracked path.",
        lambda parser: None,
        _piped(lambda text, args: logic.check_tree_clean(text)),
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
