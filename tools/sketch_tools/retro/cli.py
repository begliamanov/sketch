"""Command-line layer of the retro tool."""

from __future__ import annotations

from typing import List, Optional

from sketch_tools.core.cli import Env, Tool


def build_tool() -> Tool:
    raise NotImplementedError


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
