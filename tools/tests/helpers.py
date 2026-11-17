"""Shared test helpers."""

from __future__ import annotations

import io
from datetime import datetime
from typing import List, Optional, Tuple

from sketch_tools.core.cli import Env

FIXED_NOW = datetime(2026, 11, 12, 10, 41)


def make_env(stdin: str = "", now: datetime = FIXED_NOW) -> Tuple[Env, io.StringIO, io.StringIO]:
    """An Env with in-memory streams and a fixed clock. Returns (env, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    return Env(io.StringIO(stdin), out, err, lambda: now), out, err


def run_tool(
    main, argv: List[str], stdin: str = "", now: Optional[datetime] = None
) -> Tuple[int, str, str]:
    """Run a tool's main with fake I/O. Returns (exit code, stdout, stderr)."""
    env, out, err = make_env(stdin, now or FIXED_NOW)
    code = main(argv, env)
    return code, out.getvalue(), err.getvalue()
