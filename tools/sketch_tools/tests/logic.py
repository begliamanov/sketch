"""Pure test logic: answers about a list of `Case`s. No file access."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from sketch_tools.tests.model import Case

PASS = "PASS"
FAIL = "FAIL"
CANNOT_RUN = "CANNOT RUN"
UNKNOWN = "UNKNOWN"


def summarize(cases: Sequence[Case]) -> Dict[str, int]:
    """How many passed, failed and were skipped."""
    raise NotImplementedError


def failing(cases: Sequence[Case]) -> List[Case]:
    """The failed cases, in the order they were read."""
    raise NotImplementedError


def classify(exit_code: int, files_found: int, cases: Sequence[Case]) -> Tuple[str, str]:
    """PASS, FAIL, CANNOT RUN or UNKNOWN, with the reason (empty for PASS). UNKNOWN is for a person
    or an agent to judge: it cannot be told from the files whether the code or the environment broke."""
    raise NotImplementedError


def expect_red(cases: Sequence[Case], names: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Check that each named test ran and failed. Returns (problems, reviews): a problem is a test
    that did not run, passed or was skipped; a review is a test that failed with an error rather
    than an assertion, which a reader should look at (a broken import is not a red test)."""
    raise NotImplementedError


def skipped_diff(before: Sequence[Case], after: Sequence[Case]) -> List[str]:
    """Problems when `after` skips a test that `before` did not skip, or lost a test."""
    raise NotImplementedError


def failures_diff(before: Sequence[Case], after: Sequence[Case]) -> Tuple[bool, List[str]]:
    """(stuck, lines): stuck is True when both runs fail the same tests, at least one. The lines
    say which tests are `fixed`, `new` or `still` failing."""
    raise NotImplementedError
