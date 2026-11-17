"""Pure setup logic: from facts about the project, the steps still missing. No file access."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def parse_facts(text: str) -> Dict[str, Any]:
    """Read and validate the facts JSON. Raises UsageError for anything wrong."""
    raise NotImplementedError


def missing_steps(facts: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(kind, text) for every step that is missing, in the order to do them. A fact that is not
    given is not checked. Kinds: `safe` (one yes from the developer is enough), `ask` (safe once
    the developer gave a name), `yours` (only the developer can do it)."""
    raise NotImplementedError
