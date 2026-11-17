"""Split a shell command line into the simple commands it would run. Best effort: it follows
`;`, `&&`, `||`, `|`, newlines, `( )`, `$( )`, backticks, `bash -c '...'` and `eval`, and it strips
heredoc bodies (data, not commands). It cannot see what a script, a variable or `python -c` does."""

from __future__ import annotations

from typing import List


def simple_commands(command: str) -> List[List[str]]:
    """Every simple command in the line, as a list of words, with wrappers (`sudo`, `env`,
    `command`, `VAR=x`) removed. Raises ValueError when the line cannot be parsed."""
    raise NotImplementedError
