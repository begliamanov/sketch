"""Pure test logic: answers about a list of `Case`s. No file access."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from sketch_tools.tests.model import ERROR, FAILED, PASSED, SKIPPED, Case

PASS = "PASS"
FAIL = "FAIL"
CANNOT_RUN = "CANNOT RUN"
UNKNOWN = "UNKNOWN"


def summarize(cases: Sequence[Case]) -> Dict[str, int]:
    """How many passed, failed and were skipped."""
    return {status: sum(1 for case in cases if case.status == status) for status in (PASSED, FAILED, SKIPPED)}


def failing(cases: Sequence[Case]) -> List[Case]:
    """The failed cases, in the order they were read."""
    return [case for case in cases if case.status == FAILED]


def classify(exit_code: int, files_found: int, cases: Sequence[Case]) -> Tuple[str, str]:
    """PASS, FAIL, CANNOT RUN or UNKNOWN, with the reason (empty for PASS). UNKNOWN is for a person
    or an agent to judge: it cannot be told from the files whether the code or the environment broke."""
    failed = len(failing(cases))
    if failed:
        return FAIL, str(failed) + (" failing test" if failed == 1 else " failing tests")
    if cases:
        if exit_code == 0:
            return PASS, ""
        return UNKNOWN, (
            "every test passed but the command failed (exit " + str(exit_code) + "): "
            "something failed around the tests"
        )
    if exit_code == 0:
        if files_found == 0:
            return CANNOT_RUN, (
                "no test results were written, so nothing is known to have run: "
                "check test_results and the test command"
            )
        return CANNOT_RUN, "the result files list no tests: nothing ran"
    where = "no result file was written" if files_found == 0 else "the result files list no tests"
    return UNKNOWN, (
        "the command failed (exit " + str(exit_code) + ") and " + where
        + ": a build error in the code, or a problem in the environment?"
    )


def expect_red(cases: Sequence[Case], names: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Check that each named test ran and failed. Returns (problems, reviews): a problem is a test
    that did not run, passed or was skipped; a review is a test that failed with an error rather
    than an assertion, which a reader should look at (a broken import is not a red test)."""
    by_name: Dict[str, List[Case]] = {}
    for case in cases:
        by_name.setdefault(case.name, []).append(case)
    problems: List[str] = []
    reviews: List[str] = []
    for name in names:
        found = by_name.get(name)
        if not found:
            problems.append(name + " did not run (it is not in the results)")
        elif any(case.status == PASSED for case in found):
            problems.append(name + " passed: a new test must fail before the implementation exists")
        elif any(case.status == SKIPPED for case in found):
            problems.append(name + " was skipped: it must run and fail")
        else:
            errors = [case for case in found if case.kind == ERROR]
            if errors:
                reviews.append(
                    name + " failed with an error, not an assertion (" + errors[0].message
                    + "): check that it fails because the behavior is missing"
                )
    return problems, reviews


def skipped_diff(before: Sequence[Case], after: Sequence[Case]) -> List[str]:
    """Problems when `after` skips a test that `before` did not skip, or lost a test."""
    earlier = {case.name: case.status for case in before}
    now = {case.name for case in after}
    problems: List[str] = []
    for case in after:
        if case.status == SKIPPED and earlier.get(case.name) != SKIPPED:
            if case.name in earlier:
                problems.append(case.name + " is skipped now, it ran before")
            else:
                problems.append(case.name + " is new and skipped already")
    for name in earlier:
        if name not in now:
            problems.append(name + " is gone from the results")
    return problems


def _failing_names(cases: Sequence[Case]) -> List[str]:
    names: List[str] = []
    for case in failing(cases):
        if case.name not in names:
            names.append(case.name)
    return names


def failures_diff(before: Sequence[Case], after: Sequence[Case]) -> Tuple[bool, List[str]]:
    """(stuck, lines): stuck is True when both runs fail the same tests, at least one. The lines
    say which tests are `fixed`, `new` or `still` failing."""
    earlier, now = _failing_names(before), _failing_names(after)
    fixed = [name for name in earlier if name not in now]
    still = [name for name in earlier if name in now]
    new = [name for name in now if name not in earlier]
    lines = ["fixed: " + n for n in fixed] + ["still: " + n for n in still] + ["new: " + n for n in new]
    return bool(still) and not fixed and not new, lines
