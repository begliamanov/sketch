"""The one place this tool runs something: the project's own test command, once.

The tool otherwise never runs anything. It clears the old result files first, so a stale file can
never be mistaken for a fresh result; runs the command with stdin closed; keeps everything it
printed in a log; and copies the result files next to the log, so a later run cannot overwrite
what an earlier step is judging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sketch_tools.tests.settings import Settings


@dataclass(frozen=True)
class RunOutcome:
    command: str
    exit_code: int
    timed_out: bool
    log: Path
    results_dir: Path
    result_files: int


def run_tests(
    settings: Settings, mode: str, target: Optional[str], root: Path, logs: Path,
    now: datetime, timeout: Optional[int] = None,
) -> RunOutcome:
    """Run the configured command for `mode` from `root`. Raises DataError for a config that lacks
    what the run needs or whose `test_results` is unsafe, UsageError for a bad mode or target."""
    raise NotImplementedError
