"""Reader for JUnit XML: Gradle, pytest (`--junitxml`), Vitest and Playwright (`junit` reporter),
Jest (`jest-junit`), SwiftPM (`--xunit-output`) and most other runners."""

from __future__ import annotations

from typing import List

from sketch_tools.tests.model import Case

FORMAT = "junit-xml"


def read(text: str) -> List[Case]:
    """The test cases in one JUnit XML file. Raises ValueError when it is not one."""
    raise NotImplementedError
