"""What every reader hands back: one `Case` per test that ran, whatever the runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"
STATUSES = (PASSED, FAILED, SKIPPED)

ASSERTION = "assertion"  # the test checked something and it was wrong
ERROR = "error"  # the test blew up: an exception, a broken import, a bad setup


@dataclass(frozen=True)
class Case:
    """One test. `name` is how the runner names it (kept exactly, so it can be quoted). `message`
    is the first line of the failure or skip reason. `kind` says assertion or error when the
    format can tell, otherwise None."""

    name: str
    status: str
    message: str = ""
    kind: Optional[str] = None
