"""Command-line layer of the retro tool."""

from __future__ import annotations

import argparse
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.retro import logic


def _configure_recommend(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--story", required=True, type=int, metavar="N", help="the story that just finished")
    parser.add_argument("--flags", required=True, type=int, metavar="N", help="flagged tasks since the last retro")
    parser.add_argument("--caps", required=True, type=int, metavar="N", help="cap hits since the last retro")
    parser.add_argument("--lines-changed", required=True, type=int, metavar="N",
                        help="lines the developer changed after the PR was opened")
    parser.add_argument("--comments", required=True, type=int, metavar="N", help="review comments from the developer")
    parser.add_argument("--first-stories", type=int, default=logic.DEFAULT_FIRST_STORIES, metavar="N",
                        help="recommend for the first N stories (default %(default)s)")
    parser.add_argument("--max-lines", type=int, default=logic.DEFAULT_MAX_LINES, metavar="N",
                        help="more changed lines than this recommends one (default %(default)s)")
    parser.add_argument("--max-comments", type=int, default=logic.DEFAULT_MAX_COMMENTS, metavar="N",
                        help="more comments than this recommends one (default %(default)s)")


def _run_recommend(args: argparse.Namespace, env: Env) -> int:
    reasons = logic.recommend(args.story, args.flags, args.caps, args.lines_changed, args.comments,
                              args.first_stories, args.max_lines, args.max_comments)
    if not reasons:
        env.stdout.write("not notable\n")
    else:
        env.stdout.write("recommended\n")
        for reason in reasons:
            env.stdout.write("reason: " + reason + "\n")
    return exitcodes.OK


def build_tool() -> Tool:
    tool = Tool("retro", "Is a retro worth the developer's time?")
    tool.add_command("recommend", "apply the retro rule to the counts since the last retro", _configure_recommend, _run_recommend)
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
