"""The report of each agent role: its fields, and the rules that tie its fields together.

The source of truth for what an agent has to say is its file in core/agents/. To add a role, or a
field, add it here and to that file; the validator in schema.py needs no change.

Rules are written to survive a malformed report: they only look at a value after checking its type,
so one submission lists every problem (the schema's and the rules') in a single pass."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from sketch_tools.report.schema import Fields, Items, Mapping, Number, Spec, Text

Rules = Callable[[Dict[str, Any]], List[str]]


@dataclass
class Role:
    name: str
    scope_kind: str  # "task" (scope like t-3) or "story" (scope like story-2)
    spec: Fields
    rules: Rules
    has_skills: bool


# ---- building blocks

_TASK_ID = re.compile(r"t-\d+")
_LINE = Text()
_LINES = Items(Text())
_SHA = Text(pattern=re.compile(r"[0-9a-f]{7,40}"), pattern_hint="a git sha (7 to 40 hex characters)")
_SKILL = Fields(
    {
        "path": Text(pattern=re.compile(r"/.*/SKILL\.md"), pattern_hint="an absolute path to a SKILL.md file"),
        "rule": Text(),
        "none_applies": Text(),
    },
    required=["path"],
)
_FINDING = Fields({"what": Text(), "where": Text(), "evidence": Text()}, required=["what", "where", "evidence"])
_WIP = Fields({"built_on": Text(choices=["build", "redo"]), "why": Text()}, required=["built_on", "why"])
_VERDICT = Text(choices=["SATISFIED", "CHANGES NEEDED"])

# fields every role with skills in its brief has to report
_SKILL_FIELDS: Dict[str, Spec] = {
    "assumptions": _LINES,
    "doubts": _LINES,
    "skills_applied": Items(_SKILL),
}
_SKILL_REQUIRED = ["assumptions", "doubts", "skills_applied"]


def _text(report: Dict[str, Any], key: str) -> Optional[str]:
    value = report.get(key)
    return value if isinstance(value, str) else None


def _items(report: Dict[str, Any], key: str) -> Optional[List[Any]]:
    value = report.get(key)
    return value if isinstance(value, list) else None


def _need(report: Dict[str, Any], keys: Iterable[str], when: str) -> List[str]:
    return [key + " is required when " + when for key in keys if key not in report]


def _detail_needed(report: Dict[str, Any], without_detail: Tuple[str, ...]) -> List[str]:
    """Every outcome other than the plain success needs a `detail` saying what happened."""
    outcome = _text(report, "outcome")
    if outcome and outcome not in without_detail and not _text(report, "detail"):
        return ["detail is required when outcome is " + outcome]
    return []


def _skill_rules(report: Dict[str, Any]) -> List[str]:
    """Each skill entry gives the one concrete rule applied, or why none applies, not both."""
    problems: List[str] = []
    for index, entry in enumerate(_items(report, "skills_applied") or []):
        if isinstance(entry, dict):
            label = "skills_applied[" + str(index) + "]"
            if "rule" in entry and "none_applies" in entry:
                problems.append(label + " has both rule and none_applies: give one")
            elif "rule" not in entry and "none_applies" not in entry:
                problems.append(
                    label + " needs a rule (the concrete rule you applied) or none_applies (why none applies)"
                )
    return problems


def _verdict_rules(report: Dict[str, Any]) -> List[str]:
    """The checks the reviewers' files demand of a verdict, shared by both reviewers."""
    problems: List[str] = []
    verdict = _text(report, "verdict")
    must_fix = _items(report, "must_fix")
    if verdict == "SATISFIED" and must_fix:
        problems.append("verdict SATISFIED cannot have must_fix items")
    if verdict == "CHANGES NEEDED" and must_fix is not None and not must_fix:
        problems.append("verdict CHANGES NEEDED needs at least one must_fix item")
    return problems


# ---- implementer

_IMPLEMENTER_OUTCOMES = ("done", "test-looks-wrong", "conflicts-with-earlier-test",
                         "same-failure-twice", "outside-code-failure")

_IMPLEMENTER = Fields(
    {
        "mode": Text(choices=["implement", "fix"]),
        "outcome": Text(choices=_IMPLEMENTER_OUTCOMES),
        "detail": _LINE,
        "commits": _LINES,
        "wip": _WIP,
        "findings": Items(Fields(
            {"finding": _LINE, "status": Text(choices=["fixed", "not-fixed"]), "why": _LINE},
            required=["finding", "status"],
        )),
        **_SKILL_FIELDS,
    },
    required=["mode", "outcome", "commits"] + _SKILL_REQUIRED,
)


def _implementer_rules(report: Dict[str, Any]) -> List[str]:
    problems = _detail_needed(report, ("done",))
    outcome, mode = _text(report, "outcome"), _text(report, "mode")
    if outcome == "done" and _items(report, "commits") == []:
        problems.append("commits must list at least one commit when outcome is done")
    findings = _items(report, "findings")
    if mode == "fix" and outcome == "done" and not findings:
        problems.append("findings is required when mode is fix and outcome is done: one entry per finding")
    if mode == "implement" and findings:
        problems.append("findings only belong to fix mode, not implement")
    for index, finding in enumerate(findings or []):
        if isinstance(finding, dict) and finding.get("status") == "not-fixed" and not _text(finding, "why"):
            problems.append("findings[" + str(index) + "].why is required when status is not-fixed")
    return problems + _skill_rules(report)


# ---- test-writer

_TEST_WRITER_OUTCOMES = {
    "write": ("done", "no-clean-red", "outside-code-failure"),
    "recheck": ("test-fixed", "test-right", "outside-code-failure"),
}

_TEST_WRITER = Fields(
    {
        "mode": Text(choices=["write", "recheck"]),
        "outcome": Text(choices=["done", "no-clean-red", "outside-code-failure", "test-fixed", "test-right"]),
        "detail": _LINE,
        "files": _LINES,
        "tests_per_criterion": Mapping(re.compile(r"\d+"), "a criterion number like 1", Number(minimum=1)),
        "verification": Fields(
            {"command": _LINE, "target": _LINE, "results": _LINE, "failing": Items(_LINE, minimum=1)},
            required=["command", "target", "results", "failing"],
        ),
        "added_scenarios": _LINES,
        "concerns": _LINES,
        "wip": _WIP,
        **_SKILL_FIELDS,
    },
    required=["mode", "outcome"] + _SKILL_REQUIRED,
)


def _test_writer_rules(report: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    outcome, mode = _text(report, "outcome"), _text(report, "mode")
    allowed = _TEST_WRITER_OUTCOMES.get(mode or "")
    if outcome and allowed and outcome in _TEST_WRITER_OUTCOMES["write"] + _TEST_WRITER_OUTCOMES["recheck"] \
            and outcome not in allowed:
        problems.append(
            "outcome " + outcome + " does not fit mode " + str(mode) + " (use " + ", ".join(allowed) + ")"
        )
    problems += _detail_needed(report, ("done",))
    if mode == "write" and outcome == "done":
        when = "mode is write and outcome is done"
        problems += _need(report, ("files", "tests_per_criterion", "verification"), when)
        for key in ("files", "tests_per_criterion"):
            value = report.get(key)
            if key in report and isinstance(value, (list, dict)) and not value:
                problems.append(key + " must not be empty when " + when)
    return problems + _skill_rules(report)


# ---- reviewer (one task)

_REVIEWER = Fields(
    {
        "outcome": Text(choices=["done", "outside-code-failure"]),
        "detail": _LINE,
        "verdict": _VERDICT,
        "must_fix": Items(_FINDING),
        "nice_to_have": _LINES,
        "criteria_coverage": Items(Fields(
            {"criterion": _LINE, "test": _LINE, "status": Text(choices=["OK", "MISSING", "HOLLOW"])},
            required=["criterion", "test", "status"],
        )),
        "missing_checks": _LINES,
        **_SKILL_FIELDS,
    },
    required=["outcome"] + _SKILL_REQUIRED,
)


def _reviewer_rules(report: Dict[str, Any]) -> List[str]:
    problems = _detail_needed(report, ("done",))
    if _text(report, "outcome") == "done":
        problems += _need(report, ("verdict", "must_fix", "nice_to_have"), "outcome is done")
    problems += _verdict_rules(report)
    if _text(report, "verdict") == "SATISFIED":
        coverage = _items(report, "criteria_coverage")
        if not coverage:
            problems.append("criteria_coverage must list every criterion when the verdict is SATISFIED")
        for entry in coverage or []:
            status = entry.get("status") if isinstance(entry, dict) else None
            if status in ("MISSING", "HOLLOW"):
                problems.append("verdict SATISFIED needs every criteria_coverage status to be OK (found " + status + ")")
    return problems + _skill_rules(report)


# ---- story-reviewer

_STORY_REVIEWER = Fields(
    {
        "model": _LINE,
        "outcome": Text(choices=["done", "outside-code-failure"]),
        "detail": _LINE,
        "verdict": _VERDICT,
        "must_fix": Items(_FINDING),
        "nice_to_have": _LINES,
        "brief_delivered": Fields(
            {"status": Text(choices=["YES", "PARTLY", "NO"]), "missing": _LINES},
            required=["status", "missing"],
        ),
        "tester_result": Text(choices=["PASS", "FAIL", "CANNOT RUN"]),
        **_SKILL_FIELDS,
    },
    required=["model", "outcome"] + _SKILL_REQUIRED,
)


def _story_reviewer_rules(report: Dict[str, Any]) -> List[str]:
    problems = _detail_needed(report, ("done",))
    if _text(report, "outcome") == "done":
        problems += _need(
            report, ("verdict", "must_fix", "nice_to_have", "brief_delivered", "tester_result"), "outcome is done"
        )
    problems += _verdict_rules(report)
    tester = _text(report, "tester_result")
    if _text(report, "verdict") == "SATISFIED" and tester in ("FAIL", "CANNOT RUN"):
        problems.append("verdict SATISFIED needs tester_result PASS (got " + tester + ")")
    brief = report.get("brief_delivered")
    if isinstance(brief, dict) and brief.get("status") in ("PARTLY", "NO") and brief.get("missing") == []:
        problems.append("brief_delivered.missing must list what is missing when status is " + str(brief["status"]))
    return problems + _skill_rules(report)


# ---- tester (no skills in its brief)

_TESTER = Fields(
    {
        "mode": Text(choices=["baseline", "full"]),
        "result": Text(choices=["PASS", "FAIL", "CANNOT RUN"]),
        "branch": _LINE,
        "sha": _SHA,
        "command": _LINE,
        "log": _LINE,
        "results": _LINE,
        "counts": Fields(
            {"passed": Number(), "failed": Number(), "skipped": Number()},
            required=["passed", "failed", "skipped"],
        ),
        "failing_tests": Items(Fields({"name": _LINE, "message": _LINE}, required=["name", "message"])),
        "cannot_run_because": Text(multiline=True),
    },
    required=["mode", "result", "branch", "sha", "command", "log"],
)


def _tester_rules(report: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    result = _text(report, "result")
    failing = _items(report, "failing_tests")
    if result == "FAIL" and not failing:
        problems.append("failing_tests must list the failing tests when result is FAIL")
    if result == "CANNOT RUN" and "cannot_run_because" not in report:
        problems.append("cannot_run_because is required when result is CANNOT RUN")
    if result == "PASS":
        if failing:
            problems.append("failing_tests must be empty when result is PASS")
        if "cannot_run_because" in report:
            problems.append("cannot_run_because must be absent when result is PASS")
    return problems


# ---- task-writer

_TASK_WRITER_OUTCOMES = ("done", "too-big", "too-small", "too-vague", "outside-code-failure")

_TASK_WRITER = Fields(
    {
        "mode": Text(choices=["draft", "publish"]),
        "outcome": Text(choices=_TASK_WRITER_OUTCOMES),
        "detail": _LINE,
        "tasks": Items(Fields(
            {
                "id": Text(pattern=_TASK_ID, pattern_hint="a task id like t-3"),
                "title": _LINE,
                "blocked_by": Text(
                    pattern=re.compile(r"none|t-\d+(?:\s*,\s*t-\d+)*"), pattern_hint="none or ids like t-1, t-2"
                ),
                "scenarios": Number(minimum=1),
            },
            required=["id", "title", "blocked_by", "scenarios"],
        )),
        "story_issue": Number(minimum=1),
        "task_issues": Mapping(_TASK_ID, "a task id like t-3", Number(minimum=1)),
        "already_there": _LINES,
        **_SKILL_FIELDS,
    },
    required=["mode", "outcome"] + _SKILL_REQUIRED,
)


def _task_writer_rules(report: Dict[str, Any]) -> List[str]:
    problems = _detail_needed(report, ("done",))
    mode, outcome = _text(report, "mode"), _text(report, "outcome")
    if mode == "draft":
        problems += [key + " only belongs to publish mode" for key in ("story_issue", "task_issues", "already_there") if key in report]
    if mode == "publish" and "tasks" in report:
        problems.append("tasks only belongs to draft mode")
    if outcome == "done" and mode == "draft":
        problems += _need(report, ("tasks",), "mode is draft and outcome is done")
        if _items(report, "tasks") == []:
            problems.append("tasks must not be empty when mode is draft and outcome is done")
    if outcome == "done" and mode == "publish":
        problems += _need(report, ("story_issue", "task_issues"), "mode is publish and outcome is done")
        if report.get("task_issues") == {}:
            problems.append("task_issues must not be empty when mode is publish and outcome is done")
    return problems + _skill_rules(report)


# ---- pr-agent, retro-agent

_PR_AGENT = Fields(
    {
        "outcome": Text(choices=["done", "already-exists", "outside-code-failure"]),
        "pr": _LINE,
        "head_sha": _SHA,
        "detail": _LINE,
    },
    required=["outcome"],
)


def _pr_agent_rules(report: Dict[str, Any]) -> List[str]:
    problems = _detail_needed(report, ("done", "already-exists"))
    outcome = _text(report, "outcome")
    if outcome == "done":
        problems += _need(report, ("pr", "head_sha"), "outcome is done")
    if outcome == "already-exists":
        problems += _need(report, ("pr",), "outcome is already-exists")
    return problems


_RETRO_AGENT = Fields(
    {
        "outcome": Text(choices=["done", "blocked"]),
        "draft_path": _LINE,
        "overview": _LINE,
        "detail": _LINE,
    },
    required=["outcome"],
)


def _retro_agent_rules(report: Dict[str, Any]) -> List[str]:
    problems = _detail_needed(report, ("done",))
    if _text(report, "outcome") == "done":
        problems += _need(report, ("draft_path", "overview"), "outcome is done")
    return problems


ROLES: Dict[str, Role] = {
    role.name: role
    for role in (
        Role("implementer", "task", _IMPLEMENTER, _implementer_rules, True),
        Role("test-writer", "task", _TEST_WRITER, _test_writer_rules, True),
        Role("reviewer", "task", _REVIEWER, _reviewer_rules, True),
        Role("story-reviewer", "story", _STORY_REVIEWER, _story_reviewer_rules, True),
        Role("tester", "story", _TESTER, _tester_rules, False),
        Role("task-writer", "story", _TASK_WRITER, _task_writer_rules, True),
        Role("pr-agent", "story", _PR_AGENT, _pr_agent_rules, False),
        Role("retro-agent", "story", _RETRO_AGENT, _retro_agent_rules, False),
    )
}
