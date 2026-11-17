"""The readers: one function per result format that turns a file's text into `Case`s.

Built-in formats live here. A project adds its own by putting a `.py` file in the folder named by
`formats_dir` in `.sketch/config.md`; see `load_plugins`."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable, Dict, List, Sequence

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.tests.model import Case
from sketch_tools.tests.readers import junit, xcresult

Reader = Callable[[str], List[Case]]

BUILTIN: Dict[str, Reader] = {junit.FORMAT: junit.read, xcresult.FORMAT: xcresult.read}
BUILTIN_NAMES: Sequence[str] = tuple(BUILTIN)


def _load(path: Path) -> object:
    """Run one reader file. No bytecode is written next to it."""
    spec = importlib.util.spec_from_file_location("sketch_reader_" + path.stem, str(path))
    if spec is None or spec.loader is None:
        raise ImportError("cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def load_plugins(directory: Path) -> Dict[str, Reader]:
    """Load the project's own readers from `directory`. A reader is a `.py` file that sets
    `FORMAT = "name"` and defines `read(text) -> List[Case]` (import `Case` from
    `sketch_tools.tests.model`). Files starting with `_` are skipped. Raises UsageError when the
    folder is missing, DataError when a file cannot be loaded or repeats a name."""
    if not directory.is_dir():
        raise UsageError("folder does not exist: " + str(directory))
    found: Dict[str, Reader] = {}
    origin: Dict[str, str] = {}
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = _load(path)
        except Exception as err:  # a reader is the project's code: whatever it raises is its problem
            raise DataError("cannot load the reader " + path.name + ": " + str(err)) from err
        name = getattr(module, "FORMAT", None)
        reader = getattr(module, "read", None)
        if not isinstance(name, str) or not name.strip():
            raise DataError(path.name + ' must set FORMAT = "name"')
        if not callable(reader):
            raise DataError(path.name + " must define read(text)")
        if name in BUILTIN:
            raise DataError(path.name + ": the format name " + name + " is built in")
        if name in found:
            raise DataError(path.name + ": the format name " + name + " is already used by " + origin[name])
        found[name] = reader
        origin[name] = path.name
    return found


def get_reader(name: str, plugins: Dict[str, Reader]) -> Reader:
    """The reader for a format name. Raises UsageError listing the known names."""
    reader = plugins.get(name) or BUILTIN.get(name)
    if reader is None:
        known = list(BUILTIN) + [n for n in plugins if n not in BUILTIN]
        raise UsageError("unknown test format " + repr(name) + ": the formats are " + ", ".join(known))
    return reader
