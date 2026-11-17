"""Reader for JUnit XML: Gradle, pytest (`--junitxml`), Vitest and Playwright (`junit` reporter),
Jest (`jest-junit`), SwiftPM (`--xunit-output`) and most other runners.

The files are the project's own test output, so the standard library parser is enough."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from sketch_tools.tests.model import ASSERTION, ERROR, FAILED, PASSED, SKIPPED, Case

FORMAT = "junit-xml"


def _first_line(text: Optional[str]) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _message(node: ET.Element) -> str:
    return _first_line(node.get("message")) or _first_line(node.text)


def _case(node: ET.Element) -> Case:
    name = node.get("name")
    if not name:
        raise ValueError("a testcase has no name")
    classname = node.get("classname") or ""
    full = classname + "." + name if classname else name
    failure, error, skipped = node.find("failure"), node.find("error"), node.find("skipped")
    if failure is not None:
        return Case(full, FAILED, _message(failure), ASSERTION)
    if error is not None:
        return Case(full, FAILED, _message(error), ERROR)
    if skipped is not None:
        return Case(full, SKIPPED, _message(skipped))
    return Case(full, PASSED)


def read(text: str) -> List[Case]:
    """The test cases in one JUnit XML file. Raises ValueError when it is not one."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        raise ValueError("not valid XML: " + str(err)) from None
    if root.tag not in ("testsuites", "testsuite"):
        raise ValueError("not a JUnit file: the root element is <" + root.tag + ">")
    return [_case(node) for node in root.iter("testcase")]
