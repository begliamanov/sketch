"""Pure repo checks. Each takes the text git printed and returns a list of problems (empty = ok)."""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from sketch_tools.core.errors import UsageError
from sketch_tools.repo_check.globs import glob_to_regex

_TASK = re.compile(r"t-\d+")
_STORY_PREFIX = re.compile(r"story-\d+: \S.*")
_ANY_PREFIX = re.compile(r"(?:t-\d+|story-\d+): \S.*")
_UNRELEASED = "Unreleased"


def check_commit_prefix(subjects: str, task: Optional[str] = None) -> List[str]:
    """Commit subjects, one per line. Each must start with `t-N: ` or `story-N: `; with a task
    given, with exactly `<task>: ` or `story-N: ` (a story-end fix). Blank lines are ignored."""
    required: Optional[re.Pattern[str]] = None
    if task is not None:
        if not _TASK.fullmatch(task):
            raise UsageError("task must look like t-3 (got " + repr(task) + ")")
        required = re.compile(re.escape(task) + r": \S.*")

    problems: List[str] = []
    for line in subjects.splitlines():
        if not line.strip():
            continue
        if required is not None:
            if required.fullmatch(line) or _STORY_PREFIX.fullmatch(line):
                continue
            if _ANY_PREFIX.fullmatch(line):
                problems.append('"' + line + '" is not ' + str(task))
            else:
                problems.append('"' + line + '" has no ' + str(task) + ": prefix")
        elif not _ANY_PREFIX.fullmatch(line):
            problems.append('"' + line + '" has no task prefix (expected t-N: or story-N:)')
    return problems


def check_tests_unchanged(changed_files: str, patterns: Sequence[str]) -> List[str]:
    """File names, one per line (git diff --name-only). A problem for each one matching a test
    pattern. Raises UsageError when no pattern is given."""
    if not patterns:
        raise UsageError("give at least one --tests pattern")
    compiled = [glob_to_regex(pattern) for pattern in patterns]
    problems: List[str] = []
    for line in changed_files.splitlines():
        name = line.strip()
        if name and any(regex.fullmatch(name) for regex in compiled):
            problems.append(name + " changed after the red-test commit")
    return problems


def _added_lines(diff: str) -> Tuple[List[Tuple[Optional[str], str]], bool]:
    """The non-blank lines the diff adds, each with the `## ` heading it sits under, and whether
    the Unreleased heading is visible in the diff at all."""
    section: Optional[str] = None
    saw_unreleased = False
    added: List[Tuple[Optional[str], str]] = []
    in_hunk = False
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or not raw or raw[0] in "-\\":
            continue
        marker, content = raw[0], raw[1:]
        if marker not in " +":
            continue
        if content.startswith("## "):
            section = content[3:].strip()
            saw_unreleased = saw_unreleased or section == _UNRELEASED
        elif marker == "+" and content.strip():
            added.append((section, content))
    return added, saw_unreleased


def check_changelog(diff: str, issue: Optional[str] = None, *,
                    story_issues: Optional[List[str]] = None) -> List[str]:
    """A full-context unified diff of CHANGELOG.md. Exactly one added line under `## Unreleased`,
    a list item ending in `(#<issue>)`. With `story_issues`, one or more such lines, each ending
    in `(#<n>)` for one of those issue numbers."""
    if story_issues is not None:
        return _check_story_changelog(diff, story_issues)
    if issue is None or not re.fullmatch(r"\d+", issue):
        raise UsageError("issue must be a number (got " + repr(issue) + ")")
    added, saw_unreleased = _added_lines(diff)
    if not added:
        return ["no new line under Unreleased"]
    if not saw_unreleased:
        return [
            "cannot find the Unreleased heading in the diff: pass a full-context diff "
            "(git diff -U99999 ... -- CHANGELOG.md)"
        ]
    problems: List[str] = []
    inside = [content for section, content in added if section == _UNRELEASED]
    for section, content in added:
        if section != _UNRELEASED:
            problems.append("new line is not under Unreleased: " + content)
    if not inside:
        problems.append("no new line under Unreleased")
    elif len(inside) > 1:
        problems.append("expected one new line under Unreleased, found " + str(len(inside)))
    for content in inside:
        text = content.rstrip()
        if not text.startswith("- "):
            problems.append("new line is not a list item: " + text)
        if not text.endswith("(#" + issue + ")"):
            problems.append("new line does not end with (#" + issue + "): " + text)
    return problems


def _check_story_changelog(diff: str, story_issues: List[str]) -> List[str]:
    if not story_issues:
        raise UsageError("give at least one story issue number")
    for number in story_issues:
        if not re.fullmatch(r"\d+", number):
            raise UsageError("issue must be a number (got " + repr(number) + ")")
    added, saw_unreleased = _added_lines(diff)
    if not added:
        return ["no new line under Unreleased"]
    if not saw_unreleased:
        return [
            "cannot find the Unreleased heading in the diff: pass a full-context diff "
            "(git diff -U99999 ... -- CHANGELOG.md)"
        ]
    problems: List[str] = []
    endings = ["(#" + number + ")" for number in story_issues]
    inside = [content for section, content in added if section == _UNRELEASED]
    for section, content in added:
        if section != _UNRELEASED:
            problems.append("new line is not under Unreleased: " + content)
    if not inside:
        problems.append("no new line under Unreleased")
    for content in inside:
        text = content.rstrip()
        if not text.startswith("- "):
            problems.append("new line is not a list item: " + text)
        if not any(text.endswith(ending) for ending in endings):
            problems.append("new line does not end with " + " or ".join(endings) + ": " + text)
    return problems


def check_tree_clean(status: str) -> List[str]:
    """`git status --porcelain` output. A problem for every dirty or untracked path."""
    return ["dirty: " + line.strip() for line in status.splitlines() if line.strip()]
