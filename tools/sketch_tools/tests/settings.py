"""The keys of `.sketch/config.md` this tool reads, and what they mean."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

MODES = ("baseline", "full", "task")
TARGET_PLACEHOLDER = "{target}"


@dataclass(frozen=True)
class Settings:
    test_full: Optional[str]
    test_task: Optional[str]
    test_results: Optional[str]
    test_format: Optional[str]
    formats_dir: Optional[str]


def parse_settings(config_text: str) -> Settings:
    """Read the test keys from config text. A key that is not there is None; none is required
    here, each command asks for the ones it needs."""
    raise NotImplementedError


def command_for(settings: Settings, mode: str, target: Optional[str]) -> str:
    """The command to run: `test_full` for baseline and full, `test_task` with `{target}` replaced
    for task. Raises UsageError for a bad mode or a missing target, DataError when the config lacks
    the command or `test_task` lacks the placeholder."""
    raise NotImplementedError


def results_pattern_problem(pattern: str) -> Optional[str]:
    """Why a `test_results` pattern is unsafe to delete files by, or None. It must be relative,
    stay inside the project (no `..`), and end in `.xml` or `.json`."""
    raise NotImplementedError
