"""Pure report logic: validate a report, build and read the saved document, check, get a field.
No file access."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.report.roles import ROLES, Role

_SCOPES = {
    "task": (re.compile(r"t-\d+"), "t-3", "task"),
    "story": (re.compile(r"story-\d+"), "story-2", "story"),
}
_WRAPPER_FIELDS = ("role", "scope", "run", "submitted")


def report_name(scope: str, role: str, run: int) -> str:
    """The file name of a report: `t-3-implementer-2.json`, `story-2-tester-1.json`."""
    return scope + "-" + role + "-" + str(run) + ".json"


def known_role(role: str, scope: str) -> Role:
    """The role, after checking that the scope fits it. Raises UsageError for an unknown role or a
    scope of the wrong kind (a task role reports on `t-3`, a story role on `story-2`)."""
    spec = ROLES.get(role)
    if spec is None:
        raise UsageError("unknown role " + repr(role) + ": the roles are " + ", ".join(ROLES))
    pattern, hint, noun = _SCOPES[spec.scope_kind]
    if not pattern.fullmatch(scope):
        raise UsageError(
            "role " + role + " reports on a " + noun + ": scope must look like " + hint + " (got " + repr(scope) + ")"
        )
    return spec


def validate(role: str, scope: str, data: Any) -> List[str]:
    """Every problem with a report for this role and scope, one message each. Raises UsageError for
    an unknown role or a scope that does not fit the role."""
    spec = known_role(role, scope)
    problems = spec.spec.check(data, "")
    if isinstance(data, dict):
        problems += [p for p in spec.rules(data) if p not in problems]
    return problems


def make_document(role: str, scope: str, run: int, submitted: str, report: Any) -> str:
    """The text to save: the report with its role, scope, run and submission time around it."""
    document = {"role": role, "scope": scope, "run": run, "submitted": submitted, "report": report}
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _parse(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except ValueError:
        raise DataError("the saved report is not valid JSON") from None
    if not isinstance(data, dict):
        raise DataError("the saved report must be a JSON object")
    return data


def check_document(
    text: str, role: str, scope: str, run: int, skills: Sequence[str] = ()
) -> List[str]:
    """Check a saved document again: it parses, names this role, scope and run, the report is still
    valid, and every skill path in `skills` appears in `skills_applied`."""
    spec = known_role(role, scope)
    if skills and not spec.has_skills:
        raise UsageError("role " + role + " has no skills_applied, so skills cannot be checked")
    try:
        data = _parse(text)
    except DataError as err:
        return [str(err)]
    problems: List[str] = []
    for key, expected in (("role", role), ("scope", scope), ("run", run)):
        if key not in data:
            problems.append("the saved report has no " + key)
        elif data[key] != expected:
            problems.append("the saved report says " + key + " " + repr(data[key]) + ", expected " + repr(expected))
    if "report" not in data:
        problems.append("the saved report has no report")
        return problems
    report = data["report"]
    problems += validate(role, scope, report)
    if skills and isinstance(report, dict):
        applied = {
            entry.get("path") for entry in report.get("skills_applied", []) if isinstance(entry, dict)
        } if isinstance(report.get("skills_applied"), list) else set()
        for path in skills:
            if path not in applied:
                problems.append("skill " + path + " from the brief is not in skills_applied")
    return problems


def get_field(text: str, field: str) -> Any:
    """One field of the saved report, by dotted path (`verification.command`). The wrapper fields
    (`role`, `scope`, `run`, `submitted`) can be read too. Raises DataError when the document is
    damaged, KeyError when the field is not there."""
    data = _parse(text)
    report = data.get("report")
    parts = field.split(".")
    if isinstance(report, dict) and parts[0] in report:
        current: Any = report
    elif parts[0] in _WRAPPER_FIELDS and parts[0] in data:
        current = data
    else:
        raise KeyError(field)
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            raise KeyError(field)
        current = current[part]
    return current


def format_value(value: Any) -> str:
    """How `get` prints a value: text as is, a list of texts one per line, anything else as JSON."""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "\n".join(value)
    if isinstance(value, bool) or not isinstance(value, int):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
