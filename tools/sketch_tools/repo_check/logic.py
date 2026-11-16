"""Pure repo checks. Each takes the text git printed and returns a list of problems (empty = ok)."""

from __future__ import annotations

from typing import List, Optional, Sequence


def check_commit_prefix(subjects: str, task: Optional[str] = None) -> List[str]:
    """Commit subjects, one per line. Each must start with `t-N: ` or `story-N: `; with a task
    given, with exactly `<task>: `. Blank lines are ignored."""
    raise NotImplementedError


def check_tests_unchanged(changed_files: str, patterns: Sequence[str]) -> List[str]:
    """File names, one per line (git diff --name-only). A problem for each one matching a test
    pattern. Raises UsageError when no pattern is given."""
    raise NotImplementedError


def check_changelog(diff: str, issue: str) -> List[str]:
    """A full-context unified diff of CHANGELOG.md. Exactly one added line under `## Unreleased`,
    a list item ending in `(#<issue>)`."""
    raise NotImplementedError


def check_tree_clean(status: str) -> List[str]:
    """`git status --porcelain` output. A problem for every dirty or untracked path."""
    raise NotImplementedError
