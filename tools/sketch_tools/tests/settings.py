"""The keys of `.sketch/config.md` this tool reads, and what they mean."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.core.config_file import parse_config

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
    keys = parse_config(config_text).keys

    def value(name: str) -> Optional[str]:
        return keys.get(name) or None

    return Settings(value("test_full"), value("test_task"), value("test_results"),
                    value("test_format"), value("formats_dir"))


def command_for(settings: Settings, mode: str, target: Optional[str]) -> str:
    """The command to run: `test_full` for baseline and full, `test_task` with `{target}` replaced
    for task. Raises UsageError for a bad mode or a missing target, DataError when the config lacks
    the command or `test_task` lacks the placeholder."""
    if mode not in MODES:
        raise UsageError("mode must be one of " + ", ".join(MODES) + " (got " + repr(mode) + ")")
    if mode != "task":
        if not settings.test_full:
            raise DataError("the config has no test_full: line")
        return settings.test_full
    if target is None or not target.strip():
        raise UsageError("task mode needs --target: which tests to run")
    if "\n" in target or "\r" in target:
        raise UsageError("--target must be one line")
    if not settings.test_task:
        raise DataError("the config has no test_task: line")
    if TARGET_PLACEHOLDER not in settings.test_task:
        raise DataError("test_task must contain the placeholder " + TARGET_PLACEHOLDER)
    return settings.test_task.replace(TARGET_PLACEHOLDER, target)


def results_pattern_problem(pattern: str) -> Optional[str]:
    """Why a `test_results` pattern is unsafe to delete files by, or None. It must be relative,
    stay inside the project (no `..`), start with a folder name and not a wildcard, and end in
    `.xml` or `.json`."""
    if not pattern.strip():
        return "the pattern is empty"
    if pattern.startswith(("/", "~")) or (len(pattern) > 1 and pattern[1] == ":"):
        return "the pattern must be relative to the project (got " + repr(pattern) + ")"
    if ".." in pattern.split("/"):
        return "the pattern must stay inside the project: no .. in it (got " + repr(pattern) + ")"
    if any(char in pattern.split("/")[0] for char in "*?["):
        return "the pattern must start with a folder name, not a wildcard, so that it cannot reach the whole project (got " + repr(pattern) + ")"
    if not pattern.endswith((".xml", ".json")):
        return "the pattern must end in .xml or .json so that it only matches result files (got " + repr(pattern) + ")"
    return None
