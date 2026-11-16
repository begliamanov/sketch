"""The only places tools write files."""

from __future__ import annotations

from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    """Write text to path through a temp file and a rename, so a crash never leaves half a file."""
    raise NotImplementedError


def append_text(path: Path, text: str) -> None:
    """Append text to path, creating it if missing. Never rewrites earlier content."""
    raise NotImplementedError
