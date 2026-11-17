"""Pure guard rules: given a shell command, say why it must not run. No file access."""

from __future__ import annotations

from typing import List, Optional, Sequence


def check_command(
    command: str, protected: Sequence[str] = (), push_block: Optional[str] = None
) -> List[str]:
    """Every reason the command must not run, one message each. Empty list means allowed.

    `protected` are branch names that may not be pushed to. `push_block`, when given, is a reason
    to refuse every `git push` (for example: the state file names no feature branch)."""
    raise NotImplementedError
