"""The readers: one function per result format that turns a file's text into `Case`s.

Built-in formats live here. A project adds its own by putting a `.py` file in the folder named by
`formats_dir` in `.sketch/config.md`; see `load_plugins`."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Sequence

from sketch_tools.tests.model import Case
from sketch_tools.tests.readers import junit, xcresult

Reader = Callable[[str], List[Case]]

BUILTIN: Dict[str, Reader] = {junit.FORMAT: junit.read, xcresult.FORMAT: xcresult.read}
BUILTIN_NAMES: Sequence[str] = tuple(BUILTIN)


def load_plugins(directory: Path) -> Dict[str, Reader]:
    """Load the project's own readers from `directory`. A reader is a `.py` file that sets
    `FORMAT = "name"` and defines `read(text) -> List[Case]` (import `Case` from
    `sketch_tools.tests.model`). Files starting with `_` are skipped. Raises UsageError when the
    folder is missing, DataError when a file cannot be loaded or repeats a name."""
    raise NotImplementedError


def get_reader(name: str, plugins: Dict[str, Reader]) -> Reader:
    """The reader for a format name. Raises UsageError listing the known names."""
    raise NotImplementedError
