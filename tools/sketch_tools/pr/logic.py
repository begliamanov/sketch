"""Pure PR logic: render the description, check the PR JSON and the description. No file access."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_MAX_LINES = 20


def parse_extras(text: str) -> Dict[str, Any]:
    """Read and validate the extras JSON. Returns every key, with defaults for the optional ones.
    Raises UsageError for anything wrong."""
    raise NotImplementedError


def render_body(state_text: str, extras: Dict[str, Any], max_lines: int = DEFAULT_MAX_LINES) -> str:
    """The PR description, from the state file and the (already validated) extras. Raises DataError
    for a damaged state file or when the description is over the line limit."""
    raise NotImplementedError


def check_base(json_text: str, base: str, head: Optional[str] = None) -> List[str]:
    """Check `gh pr view --json ...` or `glab mr view --output json` output. Raises UsageError
    when the text is not a JSON object."""
    raise NotImplementedError


def check_flags(
    body: str, state_text: str, extras: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Every flag in the state file, and every unresolved item and WIP commit in the extras, must
    appear in the description."""
    raise NotImplementedError
