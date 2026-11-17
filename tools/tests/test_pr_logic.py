"""pr: the description, the PR JSON and the flags check (pure logic)."""

import json
import unittest
from pathlib import Path
from typing import Any, Dict

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.pr.logic import check_base, check_flags, parse_extras, render_body
from sketch_tools.state.logic import read_flags, read_tasks

VALID = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()
# the state when the PR is opened: every task is done or flagged, one story-end round was used
FINISHED = (VALID.replace("| in-review   |", "| done        |")
            .replace("| pending     |", "| done        |")
            .replace("story_rounds: 0/3", "story_rounds: 1/3"))
NO_FLAGS = (FINISHED.replace("| flagged     |", "| done        |")
            .replace("- t-4: tests keep failing, MissingBanner not found\n", ""))
FLAG_LINE = "- t-4: tests keep failing, MissingBanner not found"

MINIMAL: Dict[str, Any] = {
    "summary": "You can read your notes offline.\nSync and the banner follow.",
    "tests_passed": 42,
    "reviewer_model": "Opus",
}
FULL: Dict[str, Any] = dict(
    MINIMAL,
    unresolved=["Sync drops an edit when two arrive together"],
    nice_to_have=["a", "b", "c", "d", "e"],
    manual_checks=["Airplane mode: the list still opens"],
    differs=["t-2: used the existing NoteRepository (brief said new)"],
    wip_commits=["t-3: [wip] interrupted, not reviewed"],
)

TASKS_LINE = ("Tasks: #121 Read notes from cache ✓ · #122 Sync on reconnect ✓ · "
              "#123 Offline banner ✓ · #124 Pull to refresh flagged")


class ReadStateTest(unittest.TestCase):
    def test_read_tasks(self) -> None:
        tasks = read_tasks(VALID)
        self.assertEqual([t["id"] for t in tasks], ["t-1", "t-2", "t-3", "t-4"])
        self.assertEqual(tasks[1], {
            "id": "t-2", "issue": "122", "title": "Sync on reconnect", "blocked_by": "t-1",
            "status": "in-review", "attempts": "1/3", "review_rounds": "0/2",
        })

    def test_read_tasks_without_a_table_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            read_tasks(VALID.replace("## Tasks", "## Other"))

    def test_read_flags(self) -> None:
        self.assertEqual(read_flags(VALID), [FLAG_LINE])
        self.assertEqual(read_flags(NO_FLAGS), [])
        self.assertEqual(read_flags(VALID.replace("## Flags", "## Other")), [])


class ParseExtrasTest(unittest.TestCase):
    def test_minimal_extras_get_defaults(self) -> None:
        extras = parse_extras(json.dumps(MINIMAL))
        self.assertEqual(extras["summary"], MINIMAL["summary"])
        for key in ("unresolved", "nice_to_have", "manual_checks", "differs", "wip_commits"):
            self.assertEqual(extras[key], [])

    def test_full_extras_are_kept(self) -> None:
        self.assertEqual(parse_extras(json.dumps(FULL)), FULL)

    def assert_bad(self, text: str, *needles: str) -> None:
        with self.assertRaises(UsageError) as ctx:
            parse_extras(text)
        for needle in needles:
            self.assertIn(needle, str(ctx.exception))

    def test_not_json_and_not_an_object(self) -> None:
        self.assert_bad("{nope", "JSON")
        self.assert_bad("[1]", "object")
        self.assert_bad("", "JSON")

    def test_required_keys(self) -> None:
        for key in ("summary", "tests_passed", "reviewer_model"):
            with self.subTest(key=key):
                data = dict(MINIMAL)
                del data[key]
                self.assert_bad(json.dumps(data), key)

    def test_types_and_values(self) -> None:
        self.assert_bad(json.dumps(dict(MINIMAL, tests_passed="42")), "tests_passed")
        self.assert_bad(json.dumps(dict(MINIMAL, tests_passed=True)), "tests_passed")
        self.assert_bad(json.dumps(dict(MINIMAL, tests_passed=-1)), "tests_passed")
        self.assert_bad(json.dumps(dict(MINIMAL, reviewer_model="")), "reviewer_model")
        self.assert_bad(json.dumps(dict(MINIMAL, summary="")), "summary")
        self.assert_bad(json.dumps(dict(MINIMAL, summary="a\nb\nc\nd")), "summary", "3 lines")

    def test_lists_hold_one_line_strings(self) -> None:
        self.assert_bad(json.dumps(dict(MINIMAL, nice_to_have="a")), "nice_to_have", "list")
        self.assert_bad(json.dumps(dict(MINIMAL, nice_to_have=["a", ""])), "nice_to_have", "empty")
        self.assert_bad(json.dumps(dict(MINIMAL, differs=["a\nb"])), "differs", "one line")
        self.assert_bad(json.dumps(dict(MINIMAL, wip_commits=[5])), "wip_commits")

    def test_unknown_keys_are_rejected(self) -> None:
        self.assert_bad(json.dumps(dict(MINIMAL, colour="blue")), "unknown key", "colour")


class RenderBodyTest(unittest.TestCase):
    def render(self, state: str, extras: Dict[str, Any], **kwargs: Any) -> str:
        return render_body(state, parse_extras(json.dumps(extras)), **kwargs)

    def test_the_minimal_description_with_a_flag(self) -> None:
        self.assertEqual(
            self.render(FINISHED, MINIMAL),
            "Story 2: Offline notes list (#120)\n\n"
            "You can read your notes offline.\nSync and the banner follow.\n\n"
            + TASKS_LINE + "\n"
            "Tests: 42 pass. Opus reviewed it, 1 round(s), nothing blocking. Flags: see below.\n\n"
            "Flags:\n" + FLAG_LINE + "\n",
        )

    def test_the_full_description(self) -> None:
        self.assertEqual(
            self.render(FINISHED, FULL),
            "Story 2: Offline notes list (#120)\n\n"
            "You can read your notes offline.\nSync and the banner follow.\n\n"
            + TASKS_LINE + "\n"
            "Tests: 42 pass. Opus reviewed it, 1 round(s), unresolved items below. Flags: see below.\n\n"
            "Flags:\n" + FLAG_LINE + "\n"
            "- Unresolved: Sync drops an edit when two arrive together\n"
            "- WIP commit never followed by a completed step: t-3: [wip] interrupted, not reviewed\n\n"
            "Check by hand (tests can't see these):\n- Airplane mode: the list still opens\n\n"
            "Small stuff, not blocking:\n- a\n- b\n- c\n\n"
            "<details><summary>2 more nice-to-haves</summary>\n\n- d\n- e\n\n</details>\n\n"
            "Differs from the plan:\n- t-2: used the existing NoteRepository (brief said new)\n",
        )

    def test_without_flags_there_is_no_flags_block(self) -> None:
        body = self.render(NO_FLAGS, MINIMAL)
        self.assertNotIn("Flags:\n", body)
        self.assertIn("nothing blocking. Flags: none.", body)
        self.assertTrue(body.endswith("Flags: none.\n"))

    def test_the_flag_lines_are_copied_exactly(self) -> None:
        state = FINISHED.replace("tests keep failing, MissingBanner not found", "weird  spacing, \"quotes\" & é")
        self.assertIn("- t-4: weird  spacing, \"quotes\" & é\n", self.render(state, MINIMAL))

    def test_the_issue_numbers_are_optional(self) -> None:
        state = FINISHED.replace("story_issue: 120", "story_issue: none").replace("| 123   |", "| none  |")
        body = self.render(state, MINIMAL)
        self.assertTrue(body.startswith("Story 2: Offline notes list\n"))
        self.assertIn("Offline banner ✓", body)
        self.assertNotIn("#none", body)

    def test_a_task_that_is_neither_done_nor_flagged_shows_its_status(self) -> None:
        body = self.render(VALID, MINIMAL)
        self.assertIn("#122 Sync on reconnect in-review", body)

    def test_three_nice_to_haves_need_no_fold(self) -> None:
        body = self.render(FINISHED, dict(MINIMAL, nice_to_have=["a", "b", "c"]))
        self.assertNotIn("<details>", body)

    def test_the_round_count_comes_from_the_state(self) -> None:
        body = self.render(FINISHED.replace("story_rounds: 1/3", "story_rounds: 3/3"), MINIMAL)
        self.assertIn("reviewed it, 3 round(s)", body)

    def test_a_description_over_the_limit_is_an_error_that_says_so(self) -> None:
        with self.assertRaises(DataError) as ctx:
            self.render(FINISHED, dict(MINIMAL, manual_checks=["item %d" % i for i in range(20)]))
        self.assertIn("limit 20", str(ctx.exception))

    def test_flags_and_the_fold_do_not_count_towards_the_limit(self) -> None:
        extras = dict(FULL, nice_to_have=["n%d" % i for i in range(30)],
                      unresolved=["u%d" % i for i in range(15)])
        self.render(FINISHED, extras)  # must not raise

    def test_the_limit_can_be_changed(self) -> None:
        many = dict(MINIMAL, manual_checks=["item %d" % i for i in range(20)])
        self.render(FINISHED, many, max_lines=40)
        with self.assertRaises(DataError):
            self.render(FINISHED, FULL, max_lines=5)

    def test_a_damaged_state_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            self.render(FINISHED.replace("## Tasks", "## Other"), MINIMAL)
        with self.assertRaises(DataError):
            self.render(FINISHED.replace("story: 2\n", ""), MINIMAL)
        with self.assertRaises(DataError):
            self.render(FINISHED.replace("story_rounds: 1/3", "story_rounds: x"), MINIMAL)


class CheckBaseTest(unittest.TestCase):
    GITHUB = {"baseRefName": "feature/offline-notes", "headRefName": "story-2-offline-notes", "state": "OPEN"}
    GITLAB = {"target_branch": "feature/offline-notes", "source_branch": "story-2-offline-notes", "state": "opened"}

    def check(self, data: Dict[str, Any], base: str = "feature/offline-notes", head: Any = None):
        return check_base(json.dumps(data), base, head)

    def test_a_github_pr_into_the_feature_branch_is_ok(self) -> None:
        self.assertEqual(self.check(self.GITHUB), [])
        self.assertEqual(self.check(self.GITHUB, head="story-2-offline-notes"), [])

    def test_a_gitlab_mr_is_ok_too(self) -> None:
        self.assertEqual(self.check(self.GITLAB), [])
        self.assertEqual(self.check(self.GITLAB, head="story-2-offline-notes"), [])

    def test_a_wrong_base_names_both(self) -> None:
        problems = self.check(dict(self.GITHUB, baseRefName="main"))
        self.assertEqual(len(problems), 1)
        self.assertIn('"main"', problems[0])
        self.assertIn('"feature/offline-notes"', problems[0])

    def test_a_wrong_head(self) -> None:
        problems = self.check(self.GITHUB, head="story-3-other")
        self.assertEqual(len(problems), 1)
        self.assertIn("head", problems[0])

    def test_a_pr_that_is_not_open(self) -> None:
        for state in ("MERGED", "CLOSED"):
            with self.subTest(state=state):
                problems = self.check(dict(self.GITHUB, state=state))
                self.assertTrue(any(state in p and "open" in p for p in problems))
        self.assertTrue(any("merged" in p for p in self.check(dict(self.GITLAB, state="merged"))))

    def test_a_missing_state_is_not_a_problem(self) -> None:
        data = dict(self.GITHUB)
        del data["state"]
        self.assertEqual(self.check(data), [])

    def test_a_json_without_a_base_is_reported(self) -> None:
        problems = self.check({"state": "OPEN"})
        self.assertTrue(any("no base branch" in p for p in problems))

    def test_every_problem_in_one_pass(self) -> None:
        problems = self.check(dict(self.GITHUB, baseRefName="main", state="MERGED"), head="x")
        self.assertEqual(len(problems), 3)

    def test_not_a_json_object_is_a_usage_error(self) -> None:
        for text in ("", "not json", "[1]", "null"):
            with self.subTest(text=text):
                with self.assertRaises(UsageError):
                    check_base(text, "main")


class CheckFlagsTest(unittest.TestCase):
    BODY = ("Story 2: Offline notes list (#120)\n\nFlags:\n" + FLAG_LINE + "\n"
            "- Unresolved: Sync drops an edit when two arrive together\n"
            "- WIP commit never followed by a completed step: t-3: [wip] interrupted, not reviewed\n")

    def test_everything_present_is_ok(self) -> None:
        self.assertEqual(check_flags(self.BODY, FINISHED, FULL), [])

    def test_a_rendered_description_always_passes(self) -> None:
        body = render_body(FINISHED, parse_extras(json.dumps(FULL)))
        self.assertEqual(check_flags(body, FINISHED, FULL), [])

    def test_a_missing_flag_is_named(self) -> None:
        problems = check_flags("Story 2\n\nall good\n", FINISHED, None)
        self.assertEqual(len(problems), 1)
        self.assertIn("t-4: tests keep failing, MissingBanner not found", problems[0])
        self.assertIn("not in the PR description", problems[0])

    def test_a_flag_reworded_is_not_good_enough(self) -> None:
        body = "Flags:\n- t-4: tests were failing, banner missing\n"
        self.assertEqual(len(check_flags(body, FINISHED, None)), 1)

    def test_the_list_marker_does_not_matter(self) -> None:
        body = "Flags: t-4: tests keep failing, MissingBanner not found\n"
        self.assertEqual(check_flags(body, FINISHED, None), [])

    def test_missing_unresolved_items_and_wip_commits(self) -> None:
        problems = check_flags("Flags:\n" + FLAG_LINE + "\n", FINISHED, FULL)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("Sync drops an edit" in p for p in problems))
        self.assertTrue(any("[wip] interrupted" in p for p in problems))

    def test_nothing_to_check_is_ok(self) -> None:
        self.assertEqual(check_flags("anything", NO_FLAGS, None), [])
        self.assertEqual(check_flags("anything", NO_FLAGS, parse_extras(json.dumps(MINIMAL))), [])


if __name__ == "__main__":
    unittest.main()
