"""Path globs: `*` stays inside one folder, `**` crosses folders, everything else is literal."""

from __future__ import annotations

import re
from typing import Pattern


def glob_to_regex(pattern: str) -> Pattern[str]:
    """Compile a glob to a regex that must match a whole path (forward slashes)."""
    raise NotImplementedError
