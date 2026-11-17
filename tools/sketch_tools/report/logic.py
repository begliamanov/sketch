"""Pure report logic: validate a report, build and read the saved document, check, get a field.
No file access."""

from __future__ import annotations

from typing import Any, List, Sequence


def report_name(scope: str, role: str, run: int) -> str:
    """The file name of a report: `t-3-implementer-2.json`, `story-2-tester-1.json`."""
    raise NotImplementedError


def validate(role: str, scope: str, data: Any) -> List[str]:
    """Every problem with a report for this role and scope, one message each. Raises UsageError for
    an unknown role or a scope that does not fit the role."""
    raise NotImplementedError


def make_document(role: str, scope: str, run: int, submitted: str, report: Any) -> str:
    """The text to save: the report with its role, scope, run and submission time around it."""
    raise NotImplementedError


def check_document(
    text: str, role: str, scope: str, run: int, skills: Sequence[str] = ()
) -> List[str]:
    """Check a saved document again: it parses, names this role, scope and run, the report is still
    valid, and every skill path in `skills` appears in `skills_applied`."""
    raise NotImplementedError


def get_field(text: str, field: str) -> Any:
    """One field of the saved report, by dotted path (`verification.command`). Raises DataError
    when the document is damaged, KeyError when the field is not there."""
    raise NotImplementedError


def format_value(value: Any) -> str:
    """How `get` prints a value: text as is, a list of texts one per line, anything else as JSON."""
    raise NotImplementedError
