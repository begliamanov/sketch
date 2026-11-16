"""The only places tools write files."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    """Write text to path through a temp file and a rename, so a crash never leaves half a file."""
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as temp:
            temp.write(text)
            temp.flush()
            os.fsync(temp.fileno())
        if path.exists():
            shutil.copymode(str(path), temp_name)
        os.replace(temp_name, str(path))
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def append_text(path: Path, text: str) -> None:
    """Append text to path, creating it if missing. Never rewrites earlier content."""
    with open(str(path), "a", encoding="utf-8", newline="") as handle:
        handle.write(text)
