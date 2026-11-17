"""Path globs: `*` stays inside one folder, `**` crosses folders, everything else is literal."""

from __future__ import annotations

import re
from typing import List, Pattern


def glob_to_regex(pattern: str) -> Pattern[str]:
    """Compile a glob to a regex that must match a whole path (forward slashes).

    - `**/` matches any number of folders, including none
    - `**` matches anything, across folders
    - `*` matches anything inside one folder
    - `?` matches one character that is not `/`
    - every other character matches itself
    """
    out: List[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))
