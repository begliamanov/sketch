"""Command-line layer of the setup tool."""

from __future__ import annotations

import argparse
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.setup import logic


def _run_check(args: argparse.Namespace, env: Env) -> int:
    steps = logic.missing_steps(logic.parse_facts(env.stdin.read()))
    if not steps:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for number, (kind, text) in enumerate(steps, start=1):
        env.stdout.write(str(number) + ". " + kind + ": " + text + "\n")
    return exitcodes.CHECK_FAILED


def build_tool() -> Tool:
    tool = Tool("setup", "What is missing before Sketch can run in this project.")
    tool.add_command(
        "check", "stdin: facts as JSON. Prints every missing step, in order, as safe, ask or yours.",
        lambda parser: None, _run_check,
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
