"""report submit / check / get: the command-line behavior, with real files."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from sketch_tools.report import main

from tests.helpers import run_tool
from tests.report_examples import EXAMPLES, example, scope_of, with_changes


class ReportCliCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name) / "reports"
        self.dir.mkdir()

    def args(self, role: str = "implementer", run: str = "2", scope: str = "") -> "list[str]":
        default_scope = scope_of(role) if role in EXAMPLES else "t-3"
        return ["--role", role, "--scope", scope or default_scope, "--run", run, "--reports", str(self.dir)]

    def submit(self, report: Any, role: str = "implementer", run: str = "2", scope: str = ""):
        text = report if isinstance(report, str) else json.dumps(report)
        return run_tool(main, ["submit", *self.args(role, run, scope)], stdin=text)


class SubmitTest(ReportCliCase):
    def test_a_valid_report_is_saved_and_the_path_is_printed(self) -> None:
        code, out, err = self.submit(example("implementer"))
        target = self.dir / "t-3-implementer-2.json"
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "ok: saved " + str(target) + "\n")
        saved = json.loads(target.read_text())
        self.assertEqual((saved["role"], saved["scope"], saved["run"]), ("implementer", "t-3", 2))
        self.assertEqual(saved["submitted"], "2026-11-12 10:41")
        self.assertEqual(saved["report"], example("implementer"))

    def test_an_invalid_report_lists_every_problem_and_saves_nothing(self) -> None:
        report = with_changes("implementer", outcome="finished", commits=[], colour="red")
        code, out, err = self.submit(report)
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertTrue(all(line.startswith("error: ") for line in lines))
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_input_that_is_not_json_exits_3_and_saves_nothing(self) -> None:
        code, out, err = self.submit("{nope")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("JSON", err)
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_a_report_that_was_already_submitted_is_never_overwritten(self) -> None:
        self.submit(example("implementer"))
        target = self.dir / "t-3-implementer-2.json"
        before = target.read_text()
        code, out, err = self.submit(with_changes("implementer", doubts=["changed my mind"]))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("already", err)
        self.assertEqual(target.read_text(), before)

    def test_a_new_run_number_is_a_new_report(self) -> None:
        self.submit(example("implementer"), run="1")
        self.assertEqual(self.submit(example("implementer"), run="2")[0], 0)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()),
                         ["t-3-implementer-1.json", "t-3-implementer-2.json"])

    def test_an_unknown_role_a_bad_scope_or_a_bad_run_exit_3(self) -> None:
        self.assertEqual(self.submit(example("implementer"), role="janitor")[0], 3)
        # the reviewer keeps a fixed (task) scope kind; implementer and test-writer accept story-<n> since t-3
        self.assertEqual(self.submit(example("reviewer"), role="reviewer", scope="story-2")[0], 3)
        self.assertEqual(self.submit(example("implementer"), run="0")[0], 3)
        self.assertEqual(self.submit(example("implementer"), run="x")[0], 3)

    def test_a_missing_reports_folder_exits_3(self) -> None:
        argv = ["submit", "--role", "implementer", "--scope", "t-3", "--run", "1",
                "--reports", str(self.dir / "nope")]
        code, out, err = run_tool(main, argv, stdin=json.dumps(example("implementer")))
        self.assertEqual((code, out), (3, ""))
        self.assertIn("nope", err)

    def test_every_option_is_required(self) -> None:
        for missing in ("--role", "--scope", "--run", "--reports"):
            with self.subTest(missing=missing):
                argv = self.args()
                index = argv.index(missing)
                del argv[index:index + 2]
                code, _, err = run_tool(main, ["submit", *argv], stdin="{}")
                self.assertEqual(code, 3)
                self.assertIn(missing, err)

    def test_every_role_can_submit_its_example_and_check_it(self) -> None:
        for role in EXAMPLES:
            with self.subTest(role=role):
                self.assertEqual(self.submit(example(role), role=role, run="1")[0], 0)
                code, out, _ = run_tool(main, ["check", *self.args(role, "1")])
                self.assertEqual((code, out), (0, "ok\n"))


class CheckTest(ReportCliCase):
    def check(self, *extra: str, role: str = "implementer", run: str = "2"):
        return run_tool(main, ["check", *self.args(role, run), *extra])

    def test_ok_for_a_valid_report(self) -> None:
        self.submit(example("implementer"))
        self.assertEqual(self.check(), (0, "ok\n", ""))

    def test_a_report_that_was_never_submitted_is_reported(self) -> None:
        code, out, err = self.check()
        self.assertEqual((code, err), (1, ""))
        self.assertIn("no report", out)
        self.assertIn("t-3-implementer-2.json", out)

    def test_a_report_of_an_earlier_run_does_not_count(self) -> None:
        self.submit(example("implementer"), run="1")
        code, out, _ = self.check(run="2")
        self.assertEqual(code, 1)
        self.assertIn("no report", out)

    def test_a_report_edited_by_hand_into_something_invalid_fails(self) -> None:
        self.submit(example("implementer"))
        path = self.dir / "t-3-implementer-2.json"
        data = json.loads(path.read_text())
        data["report"]["outcome"] = "finished"
        path.write_text(json.dumps(data))
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("outcome", out)

    def test_skills_from_the_brief_must_all_be_in_the_report(self) -> None:
        self.submit(example("implementer"))
        ok = self.check("--skills", "/skills/kotlin/SKILL.md", "--skills", "/skills/glossary/SKILL.md")
        self.assertEqual(ok[:2], (0, "ok\n"))
        code, out, _ = self.check("--skills", "/skills/compose/SKILL.md")
        self.assertEqual(code, 1)
        self.assertIn("/skills/compose/SKILL.md", out)

    def test_skills_for_a_role_without_skills_exit_3(self) -> None:
        self.submit(example("tester"), role="tester", run="1")
        code, out, _ = run_tool(main, ["check", *self.args("tester", "1"), "--skills", "/a/SKILL.md"])
        self.assertEqual((code, out), (3, ""))


class GetTest(ReportCliCase):
    def get(self, field: str, *extra: str, role: str = "implementer", run: str = "2"):
        return run_tool(main, ["get", *self.args(role, run), *extra, field])

    def setUp(self) -> None:
        super().setUp()
        self.submit(with_changes("implementer", assumptions=["used the existing NoteRepository", "second one"]))

    def test_text_prints_as_is(self) -> None:
        self.assertEqual(self.get("outcome"), (0, "done\n", ""))

    def test_a_list_of_texts_prints_one_per_line(self) -> None:
        self.assertEqual(self.get("assumptions")[:2], (0, "used the existing NoteRepository\nsecond one\n"))

    def test_an_empty_list_prints_nothing(self) -> None:
        self.assertEqual(self.get("doubts")[:2], (0, ""))

    def test_a_nested_field_and_the_json_flag(self) -> None:
        self.assertEqual(self.get("skills_applied", "--json")[1],
                         json.dumps(example("implementer")["skills_applied"], ensure_ascii=False) + "\n")
        self.assertEqual(self.get("mode", "--json")[1], '"implement"\n')

    def test_a_missing_field_exits_1_and_names_it(self) -> None:
        code, out, err = self.get("colour")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("colour", err)

    def test_a_report_that_does_not_exist_exits_1(self) -> None:
        code, out, err = self.get("outcome", run="9")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("no report", err)

    def test_the_field_is_required(self) -> None:
        code, _, _ = run_tool(main, ["get", *self.args()])
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
