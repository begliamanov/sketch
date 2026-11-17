"""Reader for Xcode results, as printed by `xcrun xcresulttool get test-results tests --path <x>.xcresult`.

The test command writes that JSON to a file; this reader never runs Xcode tools itself."""

from __future__ import annotations

from typing import List

from sketch_tools.tests.model import Case

FORMAT = "xcresult-json"


def read(text: str) -> List[Case]:
    """The test cases in one xcresulttool JSON file. Raises ValueError when it is not one."""
    raise NotImplementedError
