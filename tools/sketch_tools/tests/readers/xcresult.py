"""Reader for Xcode results, as printed by `xcrun xcresulttool get test-results tests --path <x>.xcresult`.

The test command writes that JSON to a file; this reader never runs Xcode tools itself. The shape
was checked against a real result from Xcode 26.2: a tree of `testNodes`, where a `Test Case`
node has a `name`, a `nodeIdentifier` like `Suite/testName()`, a `result` (`Passed`, `Failed`,
`Skipped`, `Expected Failure`) and `Failure Message` children."""

from __future__ import annotations

import json
from typing import Any, List

from sketch_tools.tests.model import FAILED, PASSED, SKIPPED, Case

FORMAT = "xcresult-json"

_RESULTS = {
    "Passed": PASSED,
    "Expected Failure": PASSED,
    "Failed": FAILED,
    "Skipped": SKIPPED,
}


def _first_message(node: dict) -> str:
    for child in node.get("children", []):
        if isinstance(child, dict) and child.get("nodeType") == "Failure Message":
            for line in str(child.get("name", "")).splitlines():
                if line.strip():
                    return line.strip()
    return ""


def _case(node: dict) -> Case:
    name = node.get("nodeIdentifier") or node.get("name")
    if not name:
        raise ValueError("a Test Case node has no name")
    result = node.get("result")
    if result not in _RESULTS:
        raise ValueError("test " + str(name) + " has a result this reader does not know: " + repr(result))
    status = _RESULTS[result]
    return Case(str(name), status, _first_message(node) if status != PASSED else "")


def _walk(node: Any, found: List[Case]) -> None:
    if not isinstance(node, dict):
        return
    if node.get("nodeType") == "Test Case":
        found.append(_case(node))
        return
    for child in node.get("children", []):
        _walk(child, found)


def read(text: str) -> List[Case]:
    """The test cases in one xcresulttool JSON file. Raises ValueError when it is not one."""
    try:
        data = json.loads(text)
    except ValueError as err:
        raise ValueError("not valid JSON: " + str(err)) from None
    if not isinstance(data, dict) or not isinstance(data.get("testNodes"), list):
        raise ValueError("not xcresulttool test-results JSON: there is no testNodes list")
    found: List[Case] = []
    for node in data["testNodes"]:
        _walk(node, found)
    return found
