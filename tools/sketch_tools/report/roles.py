"""The report of each agent role: its fields, and the rules that tie fields together."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from sketch_tools.report.schema import Fields

Rules = Callable[[Dict[str, Any]], List[str]]


@dataclass
class Role:
    name: str
    scope_kind: str  # "task" (scope like t-3) or "story" (scope like story-2)
    spec: Fields
    rules: Rules
    has_skills: bool


ROLES: Dict[str, Role] = {}
