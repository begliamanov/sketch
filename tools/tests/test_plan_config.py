"""plan config-check: config.md, on text. Whether a skill file exists is a function we are given."""

import unittest
from typing import List

from sketch_tools.plan.logic import check_config

VALID = """# sketch config
tracker: github
tracker_cli: gh
default_branch: main
test_full: ./gradlew testDebugUnitTest
test_task: ./gradlew :app:testDebugUnitTest --tests "{target}"
test_paths: [**/src/test/**, Tests/**]
test_format: junit-xml
test_results: app/build/test-results/**/*.xml

skills:
  common: [/skills/common/SKILL.md]
  task-writer: [/skills/glossary/SKILL.md]
  test-writer: [/skills/testing/SKILL.md]
  implementer: [/skills/kotlin/SKILL.md, /skills/compose/SKILL.md]
  reviewer: [/skills/kotlin/SKILL.md]
  story-reviewer: []
"""


def everything_exists(path: str) -> bool:
    return True


class CheckConfigTest(unittest.TestCase):
    def problems(self, text: str, exists=everything_exists) -> List[str]:
        return check_config(text, exists)

    def assert_problem(self, text: str, *needles: str, exists=everything_exists) -> None:
        found = self.problems(text, exists)
        self.assertTrue(
            any(all(n in p for n in needles) for p in found),
            "no problem containing %r in %r" % (needles, found),
        )

    def test_the_example_is_valid(self) -> None:
        self.assertEqual(self.problems(VALID), [])

    def test_gitlab_with_glab_is_valid(self) -> None:
        text = VALID.replace("tracker: github", "tracker: gitlab").replace("tracker_cli: gh", "tracker_cli: glab")
        self.assertEqual(self.problems(text), [])

    def test_an_empty_file_has_problems(self) -> None:
        self.assertNotEqual(self.problems(""), [])

    def test_the_first_line(self) -> None:
        self.assert_problem(VALID.replace("# sketch config", "# config"), "first line")

    def test_every_key_is_required(self) -> None:
        for key in ("tracker", "tracker_cli", "default_branch", "test_full", "test_task", "test_paths",
                    "test_format", "test_results"):
            with self.subTest(key=key):
                text = "\n".join(l for l in VALID.split("\n") if not l.startswith(key + ":"))
                self.assert_problem(text, "missing key", key)

    def test_unknown_and_repeated_keys(self) -> None:
        self.assert_problem(VALID.replace("default_branch: main", "default_branch: main\ncolour: blue"), "unknown key", "colour")
        self.assert_problem(VALID.replace("default_branch: main", "default_branch: main\ndefault_branch: dev"), "default_branch", "twice")

    def test_tracker_values_and_the_pair(self) -> None:
        self.assert_problem(VALID.replace("tracker: github", "tracker: bitbucket"), "tracker", '"bitbucket"')
        self.assert_problem(VALID.replace("tracker_cli: gh", "tracker_cli: hub"), "tracker_cli", '"hub"')
        self.assert_problem(VALID.replace("tracker_cli: gh", "tracker_cli: glab"), "tracker_cli", "glab", "github", "gh")

    def test_default_branch_is_one_word(self) -> None:
        self.assert_problem(VALID.replace("default_branch: main", "default_branch: my branch"), "default_branch")
        self.assert_problem(VALID.replace("default_branch: main", "default_branch: "), "default_branch")

    def test_test_commands(self) -> None:
        self.assert_problem(VALID.replace("test_full: ./gradlew testDebugUnitTest", "test_full: "), "test_full")
        self.assert_problem(VALID.replace('--tests "{target}"', '--tests "Foo"'), "test_task", "{target}")

    def test_test_paths_must_be_a_list_of_globs(self) -> None:
        self.assert_problem(VALID.replace("test_paths: [**/src/test/**, Tests/**]", "test_paths: Tests/**"), "test_paths", "list")
        self.assert_problem(VALID.replace("test_paths: [**/src/test/**, Tests/**]", "test_paths: []"), "test_paths", "at least one")
        self.assert_problem(VALID.replace("test_paths: [**/src/test/**, Tests/**]", "test_paths: [Tests/**, ]"), "test_paths", "empty")

    def test_the_test_format_must_be_one_that_can_be_read(self) -> None:
        self.assert_problem(VALID.replace("test_format: junit-xml", "test_format: vitest"),
                            "test_format", '"vitest"', "junit-xml", "xcresult-json")
        self.assert_problem(VALID.replace("test_format: junit-xml", "test_format: "), "test_format")
        self.assertEqual(self.problems(VALID.replace("test_format: junit-xml", "test_format: xcresult-json")), [])

    def test_a_format_the_project_defines_is_known_when_it_is_listed(self) -> None:
        text = VALID.replace("test_format: junit-xml", "test_format: plain")
        self.assertNotEqual(check_config(text, everything_exists), [])
        self.assertEqual(check_config(text, everything_exists, formats=["junit-xml", "plain"]), [])

    def test_test_results_must_be_a_safe_pattern(self) -> None:
        for pattern in ("/abs/*.xml", "../x/*.xml", "build/*", "**", ""):
            with self.subTest(pattern=pattern):
                self.assert_problem(VALID.replace("test_results: app/build/test-results/**/*.xml",
                                                  "test_results: " + pattern), "test_results")

    def test_formats_dir_is_optional_but_not_empty_when_given(self) -> None:
        self.assertEqual(self.problems(VALID.replace("test_format: junit-xml\n", "test_format: junit-xml\nformats_dir: .sketch/formats\n")), [])
        self.assert_problem(VALID.replace("test_format: junit-xml\n", "test_format: junit-xml\nformats_dir: \n"), "formats_dir")

    def test_the_skills_section_and_its_roles(self) -> None:
        self.assert_problem(VALID.split("\nskills:")[0] + "\n", "missing section", "skills:")
        for role in ("common", "task-writer", "test-writer", "implementer", "reviewer", "story-reviewer"):
            with self.subTest(role=role):
                text = "\n".join(l for l in VALID.split("\n") if not l.startswith("  " + role + ":"))
                self.assert_problem(text, "missing skills role", role)
        self.assert_problem(VALID + "  tester: []\n", "unknown skills role", "tester")
        self.assert_problem(VALID.replace("  reviewer: [/skills/kotlin/SKILL.md]", "  reviewer: [/skills/kotlin/SKILL.md]\n  reviewer: []"), "reviewer", "twice")

    def test_a_role_must_be_a_list(self) -> None:
        self.assert_problem(VALID.replace("common: [/skills/common/SKILL.md]", "common: /skills/common/SKILL.md"), "common", "list")
        self.assert_problem(VALID.replace("implementer: [/skills/kotlin/SKILL.md, /skills/compose/SKILL.md]", "implementer: [/skills/kotlin/SKILL.md, ]"), "implementer", "empty")

    def test_skill_paths_must_be_absolute_and_name_a_skill_file(self) -> None:
        self.assert_problem(VALID.replace("/skills/common/SKILL.md", "skills/common/SKILL.md"), "common", "absolute")
        self.assert_problem(VALID.replace("/skills/common/SKILL.md", "/skills/common/README.md"), "common", "SKILL.md")

    def test_every_skill_file_must_exist_and_each_missing_one_is_named_with_its_role(self) -> None:
        missing = lambda path: path != "/skills/kotlin/SKILL.md"
        self.assert_problem(VALID, "does not exist", "/skills/kotlin/SKILL.md", "implementer", exists=missing)
        self.assert_problem(VALID, "does not exist", "/skills/kotlin/SKILL.md", "reviewer", exists=missing)
        found = self.problems(VALID, missing)
        self.assertEqual(len([p for p in found if "does not exist" in p]), 2)

    def test_every_problem_is_reported_in_one_pass(self) -> None:
        broken = (VALID.replace("tracker: github", "tracker: bitbucket")
                  .replace('--tests "{target}"', "")
                  .replace("test_paths: [**/src/test/**, Tests/**]", "test_paths: []")
                  .replace("  story-reviewer: []\n", ""))
        self.assertGreaterEqual(len(self.problems(broken)), 4)


if __name__ == "__main__":
    unittest.main()
