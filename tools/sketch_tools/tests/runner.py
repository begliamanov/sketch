"""The one place this tool runs something: the project's own test command, once.

The tool otherwise never runs anything. It clears the old result files first, so a stale file can
never be mistaken for a fresh result; runs the command with stdin closed; keeps everything it
printed in a log; and copies the result files next to the log, so a later run cannot overwrite
what an earlier step is judging. Unix only (it stops a runaway command by its process group)."""

from __future__ import annotations

import glob
import os
import shutil
import signal
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sketch_tools.core.errors import DataError
from sketch_tools.tests.settings import Settings, command_for, results_pattern_problem

TIMED_OUT_EXIT = 124  # the code the `timeout` command uses


@dataclass(frozen=True)
class RunOutcome:
    command: str
    exit_code: int
    timed_out: bool
    log: Path
    results_dir: Path
    result_files: int


def _matching(root: Path, pattern: str) -> List[Path]:
    """The result files the pattern matches, in path order. Files only, never folders."""
    found = glob.glob(glob.escape(str(root)) + "/" + pattern, recursive=True)
    return sorted(Path(item) for item in found if os.path.isfile(item) or os.path.islink(item))


def _free_names(logs: Path, base: str) -> "tuple[Path, Path]":
    """`<base>.log` and `<base>.results`, or with `-2`, `-3`... when a run already took the name."""
    number = 1
    while True:
        suffix = "" if number == 1 else "-" + str(number)
        log, results = logs / (base + suffix + ".log"), logs / (base + suffix + ".results")
        if not log.exists() and not results.exists():
            return log, results
        number += 1


def _execute(command: str, root: Path, log: Path, timeout: Optional[int]) -> "tuple[int, bool]":
    with open(str(log), "wb") as handle:
        process = subprocess.Popen(
            command, shell=True, cwd=str(root), stdin=subprocess.DEVNULL,
            stdout=handle, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait()
            handle.write(("\n[sketch] the command was stopped after %s seconds\n" % timeout).encode())
            return TIMED_OUT_EXIT, True
    code = process.returncode
    return (128 - code if code < 0 else code), False  # a signal shows as 128 + its number, like a shell


def run_tests(
    settings: Settings, mode: str, target: Optional[str], root: Path, logs: Path,
    now: datetime, timeout: Optional[int] = None,
) -> RunOutcome:
    """Run the configured command for `mode` from `root`. Raises DataError for a config that lacks
    what the run needs or whose `test_results` is unsafe, UsageError for a bad mode or target."""
    command = command_for(settings, mode, target)
    pattern = settings.test_results
    if not pattern:
        raise DataError("the config has no test_results: line")
    problem = results_pattern_problem(pattern)
    if problem:
        raise DataError("test_results: " + problem)

    for old in _matching(root, pattern):  # nothing left over can pass for a fresh result
        old.unlink()
    logs.mkdir(parents=True, exist_ok=True)
    log, results_dir = _free_names(logs, now.strftime("%Y%m%d-%H%M%S") + "-" + mode)

    exit_code, timed_out = _execute(command, root, log, timeout)

    results_dir.mkdir()
    files = _matching(root, pattern)
    for index, path in enumerate(files, start=1):
        shutil.copyfile(str(path), str(results_dir / ("%03d-%s" % (index, path.name))))
    return RunOutcome(command, exit_code, timed_out, log, results_dir, len(files))
