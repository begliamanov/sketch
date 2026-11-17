"""report: what each role's report must contain, and the rules that tie its fields together."""

import unittest
from typing import Any, List

from sketch_tools.core.errors import UsageError
from sketch_tools.report.logic import validate

from tests.report_examples import (
    EXAMPLES, PUBLISH, ROLES_WITH_SKILLS, STORY_ROLES, TASK_ROLES, example, scope_of, with_changes,
)


class RoleCase(unittest.TestCase):
    def problems(self, role: str, report: Any, scope: str = "") -> List[str]:
        return validate(role, scope or scope_of(role), report)

    def assert_problem(self, role: str, report: Any, *needles: str) -> None:
        found = self.problems(role, report)
        self.assertTrue(
            any(all(n in p for n in needles) for p in found),
            "no problem containing %r in %r" % (needles, found),
        )

    def assert_valid(self, role: str, report: Any) -> None:
        self.assertEqual(self.problems(role, report), [])


class GeneralTest(RoleCase):
    def test_every_example_is_valid(self) -> None:
        for role in EXAMPLES:
            with self.subTest(role=role):
                self.assert_valid(role, example(role))

    def test_an_unknown_role_lists_the_known_ones(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            validate("janitor", "t-1", {})
        message = str(ctx.exception)
        self.assertIn("janitor", message)
        for role in EXAMPLES:
            self.assertIn(role, message)

    def test_the_scope_must_fit_the_role(self) -> None:
        for role in TASK_ROLES:
            with self.subTest(role=role):
                self.assertEqual(self.problems(role, example(role), "t-12"), [])
                for bad in ("story-2", "t3", "", "T-1"):
                    with self.assertRaises(UsageError):
                        validate(role, bad, example(role))
        for role in STORY_ROLES:
            with self.subTest(role=role):
                self.assertEqual(self.problems(role, example(role), "story-12"), [])
                for bad in ("t-3", "story", "story-", "2"):
                    with self.assertRaises(UsageError):
                        validate(role, bad, example(role))

    def test_a_report_must_be_an_object(self) -> None:
        for role in EXAMPLES:
            with self.subTest(role=role):
                self.assertEqual(self.problems(role, [1]), ["the report must be an object"])

    def test_unknown_fields_are_rejected(self) -> None:
        for role in EXAMPLES:
            with self.subTest(role=role):
                self.assert_problem(role, with_changes(role, colour="red"), "colour", "not a field")

    def test_roles_with_skills_need_assumptions_doubts_and_skills(self) -> None:
        for role in ROLES_WITH_SKILLS:
            for key in ("assumptions", "doubts", "skills_applied"):
                with self.subTest(role=role, key=key):
                    self.assert_problem(role, with_changes(role, **{key: ...}), key, "required")

    def test_roles_without_skills_have_no_skills_field(self) -> None:
        for role in ("tester", "pr-agent", "retro-agent"):
            with self.subTest(role=role):
                self.assert_problem(role, with_changes(role, skills_applied=[]), "skills_applied", "not a field")

    def test_a_skill_entry_names_the_file_and_one_concrete_rule_or_why_none(self) -> None:
        good = [{"path": "/a/SKILL.md", "rule": "use immutable state"},
                {"path": "/a/SKILL.md", "none_applies": "no UI in this task"}]
        for entry in good:
            with self.subTest(entry=entry):
                self.assert_valid("implementer", with_changes("implementer", skills_applied=[entry]))
        bad = [
            ({"path": "a/SKILL.md", "rule": "x"}, "absolute"),
            ({"path": "/a/README.md", "rule": "x"}, "SKILL.md"),
            ({"rule": "x"}, "path"),
            ({"path": "/a/SKILL.md"}, "rule"),
            ({"path": "/a/SKILL.md", "rule": "x", "none_applies": "y"}, "rule"),
            ({"path": "/a/SKILL.md", "rule": ""}, "rule"),
        ]
        for entry, needle in bad:
            with self.subTest(entry=entry):
                self.assert_problem("implementer", with_changes("implementer", skills_applied=[entry]),
                                    "skills_applied[0]", needle)

    def test_no_skills_in_the_brief_is_an_empty_list(self) -> None:
        self.assert_valid("implementer", with_changes("implementer", skills_applied=[]))

    def test_list_items_are_single_lines(self) -> None:
        self.assert_problem("implementer", with_changes("implementer", doubts=["one\ntwo"]), "doubts[0]", "one line")


class ImplementerTest(RoleCase):
    def test_a_fix_round_lists_every_finding_with_its_outcome(self) -> None:
        findings = [{"finding": "Banner never hides | Banner.kt:12 | test fails", "status": "fixed"},
                    {"finding": "Rename tmp", "status": "not-fixed", "why": "conflicts with criterion 2"}]
        self.assert_valid("implementer", with_changes("implementer", mode="fix", findings=findings))

    def test_fix_mode_needs_findings_and_implement_mode_has_none(self) -> None:
        self.assert_problem("implementer", with_changes("implementer", mode="fix"), "findings", "fix")
        self.assert_problem("implementer", with_changes("implementer", mode="fix", findings=[]), "findings")
        self.assert_problem("implementer", with_changes("implementer", findings=[{"finding": "x", "status": "fixed"}]),
                            "findings", "implement")

    def test_a_finding_not_fixed_needs_its_reason(self) -> None:
        self.assert_problem("implementer",
                            with_changes("implementer", mode="fix", findings=[{"finding": "x", "status": "not-fixed"}]),
                            "findings[0]", "why")
        self.assert_problem("implementer",
                            with_changes("implementer", mode="fix", findings=[{"finding": "x", "status": "maybe"}]),
                            "findings[0].status")

    def test_done_needs_at_least_one_commit(self) -> None:
        self.assert_problem("implementer", with_changes("implementer", commits=[]), "commits", "done")

    def test_every_other_outcome_needs_a_detail_and_may_have_no_commits(self) -> None:
        for outcome in ("test-looks-wrong", "conflicts-with-earlier-test", "same-failure-twice",
                        "outside-code-failure"):
            with self.subTest(outcome=outcome):
                report = with_changes("implementer", outcome=outcome, commits=[])
                self.assert_problem("implementer", report, "detail", outcome)
                report["detail"] = "t-2's test expects 5, the criterion says 4"
                self.assert_valid("implementer", report)

    def test_an_unknown_outcome_or_mode(self) -> None:
        self.assert_problem("implementer", with_changes("implementer", outcome="finished"), "outcome", "one of")
        self.assert_problem("implementer", with_changes("implementer", mode="redo"), "mode", "one of")

    def test_wip_says_whether_it_built_on_or_redid_the_work(self) -> None:
        self.assert_valid("implementer", with_changes("implementer", wip={"built_on": "build", "why": "it was sound"}))
        self.assert_problem("implementer", with_changes("implementer", wip={"built_on": "maybe", "why": "x"}), "wip.built_on")
        self.assert_problem("implementer", with_changes("implementer", wip={"built_on": "redo"}), "wip.why")


class TestWriterTest(RoleCase):
    def test_write_done_needs_files_counts_and_the_red_verification(self) -> None:
        for key in ("files", "tests_per_criterion", "verification"):
            with self.subTest(key=key):
                self.assert_problem("test-writer", with_changes("test-writer", **{key: ...}), key, "write")
        self.assert_problem("test-writer", with_changes("test-writer", files=[]), "files")
        self.assert_problem("test-writer", with_changes("test-writer", tests_per_criterion={}), "tests_per_criterion")
        self.assert_problem("test-writer",
                            with_changes("test-writer", verification={"command": "x", "failing": []}),
                            "verification.failing")

    def test_the_verification_names_the_target_and_where_the_results_are_kept(self) -> None:
        for key in ("command", "target", "results"):
            with self.subTest(key=key):
                verification = dict(example("test-writer")["verification"])
                del verification[key]
                self.assert_problem("test-writer", with_changes("test-writer", verification=verification),
                                    "verification." + key, "required")

    def test_counts_are_keyed_by_criterion_number(self) -> None:
        self.assert_problem("test-writer", with_changes("test-writer", tests_per_criterion={"one": 2}), "tests_per_criterion", "key")
        self.assert_problem("test-writer", with_changes("test-writer", tests_per_criterion={"1": 0}), "tests_per_criterion.1")

    def test_added_scenarios_and_concerns_are_optional_lists(self) -> None:
        self.assert_valid("test-writer", with_changes("test-writer", added_scenarios=["a"], concerns=["b"]))

    def test_no_clean_red_and_outside_failures_need_a_detail(self) -> None:
        for outcome in ("no-clean-red", "outside-code-failure"):
            with self.subTest(outcome=outcome):
                report = with_changes("test-writer", outcome=outcome, files=[], tests_per_criterion={}, verification=...)
                self.assert_problem("test-writer", report, "detail")
                report["detail"] = "two attempts, the tests fail on a missing import"
                self.assert_valid("test-writer", report)

    def test_recheck_has_its_own_outcomes_and_always_a_detail(self) -> None:
        for outcome in ("test-fixed", "test-right"):
            with self.subTest(outcome=outcome):
                report = {"mode": "recheck", "outcome": outcome, "assumptions": [], "doubts": [], "skills_applied": []}
                self.assert_problem("test-writer", report, "detail")
                report["detail"] = "criterion 2 says 4: \"shows at most 4 notes\""
                self.assert_valid("test-writer", report)

    def test_the_modes_and_outcomes_must_fit(self) -> None:
        recheck = {"mode": "recheck", "outcome": "done", "detail": "x", "assumptions": [], "doubts": [], "skills_applied": []}
        self.assert_problem("test-writer", recheck, "outcome", "recheck")
        write = with_changes("test-writer", outcome="test-fixed", detail="x")
        self.assert_problem("test-writer", write, "outcome", "write")


class ReviewerTest(RoleCase):
    CHANGES = {
        "verdict": "CHANGES NEEDED",
        "must_fix": [{"what": "banner never hides", "where": "Banner.kt:12", "evidence": "./gradlew test: 1 failed"}],
        "criteria_coverage": [
            {"criterion": "1", "test": "BannerTests.shows the banner offline", "status": "OK"},
            {"criterion": "2", "test": "BannerTests.hides the banner online", "status": "HOLLOW"},
        ],
    }

    def test_changes_needed_with_findings_is_valid(self) -> None:
        self.assert_valid("reviewer", with_changes("reviewer", **self.CHANGES))

    def test_satisfied_needs_a_full_coverage_list_all_ok(self) -> None:
        self.assert_problem("reviewer", with_changes("reviewer", criteria_coverage=[]), "criteria_coverage", "SATISFIED")
        self.assert_problem("reviewer", with_changes("reviewer", criteria_coverage=...), "criteria_coverage")
        for status in ("MISSING", "HOLLOW"):
            with self.subTest(status=status):
                coverage = [{"criterion": "1", "test": "T.a", "status": status}]
                self.assert_problem("reviewer", with_changes("reviewer", criteria_coverage=coverage), "SATISFIED", status)

    def test_satisfied_cannot_have_must_fix_items(self) -> None:
        item = {"what": "x", "where": "y", "evidence": "z"}
        self.assert_problem("reviewer", with_changes("reviewer", must_fix=[item]), "SATISFIED", "must_fix")

    def test_changes_needed_needs_at_least_one_must_fix(self) -> None:
        self.assert_problem("reviewer", with_changes("reviewer", **dict(self.CHANGES, must_fix=[])), "CHANGES NEEDED", "must_fix")

    def test_every_must_fix_item_has_what_where_and_evidence(self) -> None:
        for key in ("what", "where", "evidence"):
            with self.subTest(key=key):
                item = {"what": "a", "where": "b", "evidence": "c"}
                del item[key]
                report = with_changes("reviewer", **dict(self.CHANGES, must_fix=[item]))
                self.assert_problem("reviewer", report, "must_fix[0]." + key, "required")

    def test_a_coverage_entry_has_a_valid_status(self) -> None:
        coverage = [{"criterion": "1", "test": "T.a", "status": "FINE"}]
        self.assert_problem("reviewer", with_changes("reviewer", criteria_coverage=coverage), "criteria_coverage[0].status")

    def test_outside_code_failure_stands_in_for_the_review(self) -> None:
        report = {"outcome": "outside-code-failure", "assumptions": [], "doubts": [], "skills_applied": []}
        self.assert_problem("reviewer", report, "detail")
        report["detail"] = "gh is not logged in"
        self.assert_valid("reviewer", report)

    def test_a_done_review_needs_a_verdict(self) -> None:
        self.assert_problem("reviewer", with_changes("reviewer", verdict=...), "verdict", "done")
        self.assert_problem("reviewer", with_changes("reviewer", verdict="MAYBE"), "verdict", "one of")

    def test_missing_checks_are_an_optional_list(self) -> None:
        self.assert_valid("reviewer", with_changes("reviewer", missing_checks=["changelog"]))


class StoryReviewerTest(RoleCase):
    def test_satisfied_needs_a_passing_tester(self) -> None:
        for result in ("FAIL", "CANNOT RUN"):
            with self.subTest(result=result):
                self.assert_problem("story-reviewer", with_changes("story-reviewer", tester_result=result),
                                    "SATISFIED", "tester_result")

    def test_satisfied_cannot_have_must_fix_items(self) -> None:
        item = {"what": "x", "where": "y", "evidence": "z"}
        self.assert_problem("story-reviewer", with_changes("story-reviewer", must_fix=[item]), "SATISFIED", "must_fix")

    def test_changes_needed_needs_must_fix_items(self) -> None:
        report = with_changes("story-reviewer", verdict="CHANGES NEEDED", tester_result="FAIL")
        self.assert_problem("story-reviewer", report, "CHANGES NEEDED", "must_fix")
        report["must_fix"] = [{"what": "BannerTests.hides", "where": "BannerTests", "evidence": "tester log"}]
        self.assert_valid("story-reviewer", report)

    def test_brief_delivered_lists_what_is_missing_unless_yes(self) -> None:
        for status in ("PARTLY", "NO"):
            with self.subTest(status=status):
                report = with_changes("story-reviewer", brief_delivered={"status": status, "missing": []})
                self.assert_problem("story-reviewer", report, "brief_delivered.missing", status)
                report["brief_delivered"]["missing"] = ["the banner never shows"]
                self.assert_valid("story-reviewer", report)
        self.assert_problem("story-reviewer", with_changes("story-reviewer", brief_delivered={"status": "MOSTLY", "missing": []}),
                            "brief_delivered.status")

    def test_the_model_is_required(self) -> None:
        self.assert_problem("story-reviewer", with_changes("story-reviewer", model=...), "model", "required")
        self.assert_problem("story-reviewer", with_changes("story-reviewer", model=""), "model")

    def test_outside_code_failure_stands_in_for_the_review(self) -> None:
        report = {"model": "Opus", "outcome": "outside-code-failure", "detail": "network down",
                  "assumptions": [], "doubts": [], "skills_applied": []}
        self.assert_valid("story-reviewer", report)


class TesterTest(RoleCase):
    def test_a_failing_run_lists_the_failing_tests(self) -> None:
        report = with_changes("tester", result="FAIL", counts={"passed": 40, "failed": 2, "skipped": 0})
        self.assert_problem("tester", report, "failing_tests", "FAIL")
        report["failing_tests"] = [{"name": "BannerTests.hides", "message": "expected hidden"}]
        self.assert_valid("tester", report)

    def test_a_cannot_run_says_why(self) -> None:
        report = with_changes("tester", result="CANNOT RUN", counts=...)
        self.assert_problem("tester", report, "cannot_run_because", "CANNOT RUN")
        report["cannot_run_because"] = "Could not resolve com.example:lib (401)"
        self.assert_valid("tester", report)

    def test_a_pass_has_no_failures_and_no_excuse(self) -> None:
        self.assert_problem("tester", with_changes("tester", failing_tests=[{"name": "a", "message": "b"}]), "PASS", "failing_tests")
        self.assert_problem("tester", with_changes("tester", cannot_run_because="x"), "PASS", "cannot_run_because")

    def test_the_facts_are_required_and_checked(self) -> None:
        for key in ("mode", "result", "branch", "sha", "command", "log"):
            with self.subTest(key=key):
                self.assert_problem("tester", with_changes("tester", **{key: ...}), key, "required")
        self.assert_problem("tester", with_changes("tester", sha="xyz"), "sha")
        self.assert_problem("tester", with_changes("tester", mode="task"), "mode", "one of")
        self.assert_problem("tester", with_changes("tester", result="OK"), "result", "one of")

    def test_the_results_folder_is_an_optional_field(self) -> None:
        self.assert_valid("tester", with_changes("tester", results=".sketch/logs/20261112-104100-full.results"))
        self.assert_problem("tester", with_changes("tester", results=""), "results")

    def test_counts_are_optional_but_whole(self) -> None:
        self.assert_valid("tester", with_changes("tester", counts=...))
        self.assert_problem("tester", with_changes("tester", counts={"passed": "42", "failed": 0, "skipped": 0}), "counts.passed")


class TaskWriterTest(RoleCase):
    def test_draft_done_lists_the_tasks(self) -> None:
        self.assert_problem("task-writer", with_changes("task-writer", tasks=...), "tasks", "draft")
        self.assert_problem("task-writer", with_changes("task-writer", tasks=[]), "tasks")
        bad = [{"id": "x", "title": "T", "blocked_by": "none", "scenarios": 3}]
        self.assert_problem("task-writer", with_changes("task-writer", tasks=bad), "tasks[0].id")

    def test_publish_done_lists_the_issue_numbers(self) -> None:
        self.assert_valid("task-writer", dict(PUBLISH))
        for key in ("story_issue", "task_issues"):
            with self.subTest(key=key):
                report = dict(PUBLISH)
                del report[key]
                self.assert_problem("task-writer", report, key, "publish")
        self.assert_problem("task-writer", dict(PUBLISH, task_issues={}), "task_issues")
        self.assert_problem("task-writer", dict(PUBLISH, task_issues={"t1": 5}), "task_issues", "key")

    def test_each_mode_keeps_to_its_own_fields(self) -> None:
        self.assert_problem("task-writer", with_changes("task-writer", story_issue=120), "story_issue", "publish")
        self.assert_problem("task-writer", dict(PUBLISH, tasks=[]), "tasks", "draft")

    def test_other_outcomes_say_why(self) -> None:
        for outcome in ("too-big", "too-small", "too-vague", "outside-code-failure"):
            with self.subTest(outcome=outcome):
                report = with_changes("task-writer", outcome=outcome, tasks=...)
                self.assert_problem("task-writer", report, "detail")
                report["detail"] = "9 tasks: split after t-4"
                self.assert_valid("task-writer", report)


class PrAgentTest(RoleCase):
    def test_done_needs_the_pr_and_the_head_sha(self) -> None:
        self.assert_problem("pr-agent", with_changes("pr-agent", pr=...), "pr", "done")
        self.assert_problem("pr-agent", with_changes("pr-agent", head_sha=...), "head_sha", "done")
        self.assert_problem("pr-agent", with_changes("pr-agent", head_sha="zz"), "head_sha")

    def test_already_exists_needs_the_pr(self) -> None:
        self.assert_valid("pr-agent", {"outcome": "already-exists", "pr": "45"})
        self.assert_problem("pr-agent", {"outcome": "already-exists"}, "pr")

    def test_a_failure_needs_a_detail(self) -> None:
        self.assert_problem("pr-agent", {"outcome": "outside-code-failure"}, "detail")
        self.assert_valid("pr-agent", {"outcome": "outside-code-failure", "detail": "gh pr create: 401"})


class RetroAgentTest(RoleCase):
    def test_done_needs_the_draft_and_an_overview(self) -> None:
        self.assert_problem("retro-agent", with_changes("retro-agent", draft_path=...), "draft_path", "done")
        self.assert_problem("retro-agent", with_changes("retro-agent", overview=...), "overview", "done")

    def test_blocked_needs_a_detail(self) -> None:
        self.assert_problem("retro-agent", {"outcome": "blocked"}, "detail")
        self.assert_valid("retro-agent", {"outcome": "blocked", "detail": "no journal"})


if __name__ == "__main__":
    unittest.main()
