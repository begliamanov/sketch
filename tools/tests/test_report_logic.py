"""report: names, the saved document, check, and getting a field (pure logic)."""

import json
import unittest

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.report.logic import (
    check_document, format_value, get_field, make_document, report_name,
)

from tests.report_examples import example, scope_of, with_changes

WHEN = "2026-11-12 10:41"


def document(role: str = "implementer", run: int = 2, **changes: object) -> str:
    return make_document(role, scope_of(role), run, WHEN, with_changes(role, **changes))


class ReportNameTest(unittest.TestCase):
    def test_names(self) -> None:
        self.assertEqual(report_name("t-3", "implementer", 2), "t-3-implementer-2.json")
        self.assertEqual(report_name("story-2", "story-reviewer", 1), "story-2-story-reviewer-1.json")
        self.assertEqual(report_name("t-12", "test-writer", 10), "t-12-test-writer-10.json")


class MakeDocumentTest(unittest.TestCase):
    def test_the_report_is_wrapped_with_who_what_and_when(self) -> None:
        text = document()
        data = json.loads(text)
        self.assertEqual(list(data), ["role", "scope", "run", "submitted", "report"])
        self.assertEqual((data["role"], data["scope"], data["run"], data["submitted"]),
                         ("implementer", "t-3", 2, WHEN))
        self.assertEqual(data["report"], example("implementer"))

    def test_the_text_is_stable_readable_and_ends_with_a_newline(self) -> None:
        text = document()
        self.assertTrue(text.endswith("}\n"))
        self.assertIn('\n  "role": "implementer",\n', text)
        self.assertEqual(document(), document())

    def test_text_is_kept_exactly_including_non_ascii(self) -> None:
        text = document(assumptions=["café  spacing, \"quotes\" and é"])
        self.assertIn("café  spacing", text)
        self.assertEqual(json.loads(text)["report"]["assumptions"], ["café  spacing, \"quotes\" and é"])


class CheckDocumentTest(unittest.TestCase):
    def check(self, text: str, role: str = "implementer", scope: str = "", run: int = 2, **kwargs: object):
        return check_document(text, role, scope or scope_of(role), run, **kwargs)  # type: ignore[arg-type]

    def test_a_saved_valid_document_is_ok(self) -> None:
        self.assertEqual(self.check(document()), [])

    def test_text_that_is_not_json_or_not_an_object(self) -> None:
        self.assertEqual(self.check("{nope"), ["the saved report is not valid JSON"])
        self.assertEqual(self.check("[1]"), ["the saved report must be a JSON object"])

    def test_the_document_must_name_this_role_scope_and_run(self) -> None:
        data = json.loads(document())
        for key, value, needle in (("role", "reviewer", "role"), ("scope", "t-9", "scope"), ("run", 7, "run")):
            with self.subTest(key=key):
                broken = dict(data, **{key: value})
                problems = self.check(json.dumps(broken))
                self.assertTrue(any(needle in p and str(value) in p for p in problems), problems)

    def test_a_missing_wrapper_field_is_reported(self) -> None:
        data = json.loads(document())
        del data["report"]
        self.assertTrue(any("report" in p for p in self.check(json.dumps(data))))

    def test_the_report_is_checked_again(self) -> None:
        problems = self.check(document(outcome="finished"))
        self.assertTrue(any("outcome" in p for p in problems))

    def test_every_brief_skill_must_be_in_skills_applied(self) -> None:
        self.assertEqual(self.check(document(), skills=["/skills/kotlin/SKILL.md", "/skills/glossary/SKILL.md"]), [])
        problems = self.check(document(), skills=["/skills/kotlin/SKILL.md", "/skills/compose/SKILL.md"])
        self.assertEqual(len(problems), 1)
        self.assertIn("/skills/compose/SKILL.md", problems[0])
        self.assertIn("skills_applied", problems[0])

    def test_skills_on_a_role_without_skills_is_a_usage_error(self) -> None:
        text = make_document("tester", "story-2", 1, WHEN, example("tester"))
        with self.assertRaises(UsageError):
            check_document(text, "tester", "story-2", 1, skills=["/a/SKILL.md"])


class GetFieldTest(unittest.TestCase):
    def test_a_top_level_field_and_a_nested_one(self) -> None:
        self.assertEqual(get_field(document(), "outcome"), "done")
        self.assertEqual(get_field(document(), "commits"), ["t-3: add the offline banner"])
        text = document("test-writer", run=1)
        self.assertEqual(get_field(text, "verification.command"), "./gradlew test --tests BannerTests")
        self.assertEqual(get_field(text, "tests_per_criterion.1"), 3)

    def test_the_wrapper_fields_can_be_read_too(self) -> None:
        self.assertEqual(get_field(document(), "scope"), "t-3")
        self.assertEqual(get_field(document(), "submitted"), WHEN)

    def test_a_missing_field_is_a_key_error_naming_it(self) -> None:
        for field in ("colour", "verification.command", "outcome.x"):
            with self.subTest(field=field):
                with self.assertRaises(KeyError) as ctx:
                    get_field(document(), field)
                self.assertIn(field, str(ctx.exception))

    def test_a_damaged_document_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            get_field("{nope", "outcome")
        with self.assertRaises(DataError):
            get_field("[1]", "outcome")


class FormatValueTest(unittest.TestCase):
    def test_how_values_print(self) -> None:
        self.assertEqual(format_value("done"), "done")
        self.assertEqual(format_value(42), "42")
        self.assertEqual(format_value(["a", "b"]), "a\nb")
        self.assertEqual(format_value([]), "")
        self.assertEqual(format_value([{"what": "x"}]), '[{"what": "x"}]')
        self.assertEqual(format_value({"a": 1}), '{"a": 1}')
        self.assertEqual(format_value(True), "true")
        self.assertEqual(format_value("café"), "café")
        self.assertEqual(format_value([{"w": "é"}]), '[{"w": "é"}]')


if __name__ == "__main__":
    unittest.main()
