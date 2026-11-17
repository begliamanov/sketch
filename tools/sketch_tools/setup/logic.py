"""Pure setup logic: from facts about the project, the steps still missing. No file access.

The steps and who may do them come from the orchestrator rules ("Setup gaps"): what is safe to run
on one yes, what needs a name the developer gives, what only the developer can do."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from sketch_tools.core.errors import UsageError

_BOOLS = ("git_repo", "has_commit", "has_remote", "cli_logged_in", "sketch_dir", "sketch_excluded",
          "has_config", "has_docs", "on_default_branch", "feature_pushed")
_KEYS = _BOOLS + ("tracker_cli",)


def parse_facts(text: str) -> Dict[str, Any]:
    """Read and validate the facts JSON. Raises UsageError for anything wrong."""
    try:
        facts = json.loads(text)
    except ValueError as err:
        raise UsageError("the facts are not valid JSON: " + str(err)) from None
    if not isinstance(facts, dict):
        raise UsageError("the facts must be a JSON object")
    for key, value in facts.items():
        if key not in _KEYS:
            raise UsageError("unknown fact: " + key)
        if key in _BOOLS and not isinstance(value, bool):
            raise UsageError(key + " must be true or false")
        if key == "tracker_cli" and value not in ("gh", "glab"):
            raise UsageError("tracker_cli must be gh or glab")
    return facts


def missing_steps(facts: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(kind, text) for every step that is missing, in the order to do them. A fact that is not
    given is not checked. Kinds: `safe` (one yes from the developer is enough), `ask` (safe once
    the developer gave a name), `yours` (only the developer can do it)."""
    cli = facts.get("tracker_cli", "gh")
    create = (
        "gh repo create <name> --private --source=. --remote=origin" if cli == "gh"
        else "glab repo create <name> --private"
    )
    steps: List[Tuple[str, str]] = []

    def missing(key: str) -> bool:
        return facts.get(key) is False

    if missing("git_repo"):
        steps.append(("safe", "git init"))
    if missing("has_commit"):
        steps.append(("safe", 'git add -A && git commit -m "Initial commit"'))
    if missing("has_remote"):
        steps.append(("ask", create + " (the developer names it and picks the visibility)"))
    if missing("cli_logged_in"):
        steps.append(("yours", cli + " auth login"))
    if missing("sketch_dir"):
        steps.append(("safe", "mkdir -p .sketch/logs .sketch/retro .sketch/reports"))
    if missing("sketch_excluded"):
        steps.append(("safe", 'echo ".sketch/" >> .git/info/exclude'))
    if missing("has_config"):
        steps.append(("yours", "run /tune-skills"))
    if missing("has_docs"):
        steps.append(("safe", "mkdir -p docs/adr"))
    if facts.get("on_default_branch") is True:
        steps.append(("ask", "git switch -c feature/<name> (a name the developer agrees to)"))
    if missing("feature_pushed"):
        steps.append(("ask", "git push -u origin <feature-branch> (only during /sketch, the first and only push to it)"))
    return steps
