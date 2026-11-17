"""plan brief-skills, issues-todo and detect-tracker."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.plan import main
from sketch_tools.plan.briefing import brief_skills, parse_extra_skills
from sketch_tools.plan.issues import issues_todo, parse_issue_facts
from sketch_tools.plan.tracker import detect_tracker, remote_host

from tests.helpers import run_tool
from tests.test_plan_config import VALID as CONFIG
from tests.test_plan_tasks import VALID as TASKS


def everything_exists(path: str) -> bool:
    return True


class ParseExtraSkillsTest(unittest.TestCase):
    def test_none_and_empty_mean_no_skills(self) -> None:
        self.assertEqual(parse_extra_skills("none"), [])
        self.assertEqual(parse_extra_skills(""), [])
        self.assertEqual(parse_extra_skills("   "), [])

    def test_paths_split_on_commas_and_spaces(self) -> None:
        self.assertEqual(parse_extra_skills("/a/SKILL.md"), ["/a/SKILL.md"])
        self.assertEqual(parse_extra_skills("/a/SKILL.md, /b/SKILL.md"), ["/a/SKILL.md", "/b/SKILL.md"])
        self.assertEqual(parse_extra_skills("/a/SKILL.md /b/SKILL.md"), ["/a/SKILL.md", "/b/SKILL.md"])


class BriefSkillsTest(unittest.TestCase):
    def brief(self, role: str, extra=(), exists=everything_exists):
        return brief_skills(CONFIG, role, extra, exists)

    def test_common_first_then_the_roles_own_list(self) -> None:
        self.assertEqual(self.brief("implementer"), (
            ["/skills/common/SKILL.md", "/skills/kotlin/SKILL.md", "/skills/compose/SKILL.md"], []))
        self.assertEqual(self.brief("task-writer")[0], ["/skills/common/SKILL.md", "/skills/glossary/SKILL.md"])

    def test_a_role_with_an_empty_list_gets_common_only(self) -> None:
        self.assertEqual(self.brief("story-reviewer"), (["/skills/common/SKILL.md"], []))

    def test_the_stories_extra_skills_come_last_for_every_role(self) -> None:
        paths, _ = self.brief("reviewer", ["/extra/SKILL.md"])
        self.assertEqual(paths, ["/skills/common/SKILL.md", "/skills/kotlin/SKILL.md", "/extra/SKILL.md"])

    def test_nothing_is_listed_twice(self) -> None:
        paths, _ = self.brief("implementer", ["/skills/kotlin/SKILL.md", "/extra/SKILL.md", "/extra/SKILL.md"])
        self.assertEqual(paths, ["/skills/common/SKILL.md", "/skills/kotlin/SKILL.md",
                                 "/skills/compose/SKILL.md", "/extra/SKILL.md"])

    def test_picks_narrow_the_roles_own_list_but_never_common_or_extras(self) -> None:
        paths, _ = brief_skills(CONFIG, "implementer", ["/extra/SKILL.md"], everything_exists, picks=["compose"])
        self.assertEqual(paths, ["/skills/common/SKILL.md", "/skills/compose/SKILL.md", "/extra/SKILL.md"])

    def test_picks_that_are_not_in_the_roles_list_are_ignored(self) -> None:
        paths, _ = brief_skills(CONFIG, "implementer", [], everything_exists, picks=["glossary"])
        self.assertEqual(paths, ["/skills/common/SKILL.md"])

    def test_the_story_reviewer_always_keeps_its_full_list(self) -> None:
        paths, _ = brief_skills(CONFIG.replace("story-reviewer: []", "story-reviewer: [/skills/kotlin/SKILL.md]"),
                                "story-reviewer", [], everything_exists, picks=["compose"])
        self.assertEqual(paths, ["/skills/common/SKILL.md", "/skills/kotlin/SKILL.md"])

    def test_roles_that_never_get_skills_get_none(self) -> None:
        for role in ("tester", "pr-agent", "retro-agent"):
            with self.subTest(role=role):
                self.assertEqual(self.brief(role, ["/extra/SKILL.md"]), ([], []))

    def test_an_unknown_role_lists_the_known_ones(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            self.brief("janitor")
        for role in ("janitor", "implementer", "tester"):
            self.assertIn(role, str(ctx.exception))

    def test_common_is_not_a_role_to_ask_for(self) -> None:
        with self.assertRaises(UsageError):
            self.brief("common")

    def test_a_config_without_the_role_or_with_a_bad_list_is_a_data_error(self) -> None:
        with self.assertRaises(DataError) as ctx:
            brief_skills(CONFIG.replace("  implementer: [/skills/kotlin/SKILL.md, /skills/compose/SKILL.md]\n", ""),
                         "implementer", [], everything_exists)
        self.assertIn("implementer", str(ctx.exception))
        with self.assertRaises(DataError):
            brief_skills(CONFIG.replace("common: [/skills/common/SKILL.md]", "common: nope"), "implementer", [], everything_exists)

    def test_a_skill_file_that_does_not_exist_is_a_problem_naming_it_and_where_it_came_from(self) -> None:
        paths, problems = self.brief("implementer", ["/extra/SKILL.md"], exists=lambda p: p not in ("/skills/kotlin/SKILL.md", "/extra/SKILL.md"))
        self.assertEqual(len(paths), 4)
        self.assertEqual(len(problems), 2)
        self.assertIn("/skills/kotlin/SKILL.md", problems[0])
        self.assertIn("does not exist", problems[0])
        self.assertIn("/extra/SKILL.md", problems[1])
        self.assertIn("extra", problems[1])

    def test_an_extra_skill_must_be_an_absolute_path_to_a_skill_file(self) -> None:
        for bad in ("extra/SKILL.md", "/extra/README.md"):
            with self.subTest(path=bad):
                with self.assertRaises(DataError):
                    self.brief("implementer", [bad])


FACTS_EMPTY: Dict[str, Any] = {"issues": [], "links": []}


class ParseIssueFactsTest(unittest.TestCase):
    def test_valid_facts(self) -> None:
        facts = {"issues": [{"number": 120, "title": "Story 2: x"}], "links": [{"blocked": "t-2", "by": "t-1"}]}
        self.assertEqual(parse_issue_facts(json.dumps(facts)), facts)
        self.assertEqual(parse_issue_facts("{}"), {"issues": [], "links": []})

    def assert_bad(self, text: str, *needles: str) -> None:
        with self.assertRaises(UsageError) as ctx:
            parse_issue_facts(text)
        for needle in needles:
            self.assertIn(needle, str(ctx.exception))

    def test_bad_facts(self) -> None:
        self.assert_bad("{nope", "JSON")
        self.assert_bad("[1]", "object")
        self.assert_bad(json.dumps({"tickets": []}), "unknown", "tickets")
        self.assert_bad(json.dumps({"issues": "x"}), "issues", "list")
        self.assert_bad(json.dumps({"issues": [{"number": "1", "title": "t"}]}), "number")
        self.assert_bad(json.dumps({"issues": [{"number": 0, "title": "t"}]}), "number")
        self.assert_bad(json.dumps({"issues": [{"number": 1, "title": ""}]}), "title")
        self.assert_bad(json.dumps({"links": [{"blocked": "x", "by": "t-1"}]}), "links", "task id")


class IssuesTodoTest(unittest.TestCase):
    ALL_TODO = [
        "todo story: Story 2: Offline notes list",
        "todo task t-1: t-1: Read notes from cache",
        "todo task t-2: t-2: Sync on reconnect",
        "todo task t-3: t-3: Offline banner",
        "todo task t-4: t-4: Retry failed syncs",
        "todo link t-2 t-1",
        "todo link t-3 t-1",
        "todo link t-4 t-2",
        "todo link t-4 t-3",
    ]

    def test_nothing_exists_yet(self) -> None:
        self.assertEqual(issues_todo(TASKS, FACTS_EMPTY), self.ALL_TODO)

    def test_what_exists_is_reported_and_only_the_rest_is_todo(self) -> None:
        facts = {"issues": [{"number": 120, "title": "Story 2: Offline notes list"},
                            {"number": 121, "title": "t-1: Read notes from cache"},
                            {"number": 122, "title": "t-2: Sync (title edited by hand)"}],
                 "links": [{"blocked": "t-2", "by": "t-1"}]}
        lines = issues_todo(TASKS, facts)
        self.assertEqual(lines[:3], ["have story: #120", "have task t-1: #121", "have task t-2: #122"])
        self.assertEqual(lines[3:5], ["todo task t-3: t-3: Offline banner", "todo task t-4: t-4: Retry failed syncs"])
        self.assertEqual(lines[5:], ["have link t-2 t-1", "todo link t-3 t-1", "todo link t-4 t-2", "todo link t-4 t-3"])

    def test_everything_there_means_nothing_is_todo(self) -> None:
        facts = {"issues": [{"number": 120, "title": "Story 2: Offline notes list"}]
                 + [{"number": 121 + i, "title": "t-%d: x" % (i + 1)} for i in range(4)],
                 "links": [{"blocked": "t-2", "by": "t-1"}, {"blocked": "t-3", "by": "t-1"},
                           {"blocked": "t-4", "by": "t-2"}, {"blocked": "t-4", "by": "t-3"}]}
        self.assertFalse(any(line.startswith("todo") for line in issues_todo(TASKS, facts)))

    def test_other_issues_in_the_list_are_ignored(self) -> None:
        facts = {"issues": [{"number": 5, "title": "Fix typo in README"}, {"number": 9, "title": "Story 7: other story"}], "links": []}
        self.assertEqual(issues_todo(TASKS, facts), self.ALL_TODO)

    def test_two_issues_for_one_task_or_for_the_story_is_a_data_error(self) -> None:
        for title, needle in (("t-1: again", "t-1"), ("Story 2: again", "story")):
            with self.subTest(title=title):
                facts = {"issues": [{"number": 121, "title": "t-1: Read notes from cache"},
                                    {"number": 120, "title": "Story 2: Offline notes list"},
                                    {"number": 130, "title": title}], "links": []}
                with self.assertRaises(DataError) as ctx:
                    issues_todo(TASKS, facts)
                self.assertIn(needle, str(ctx.exception))
                self.assertIn("#130", str(ctx.exception))

    def test_a_tasks_file_with_problems_is_a_data_error(self) -> None:
        with self.assertRaises(DataError) as ctx:
            issues_todo(TASKS.replace("# Tasks for story 2: Offline notes list", "# Tasks"), FACTS_EMPTY)
        self.assertIn("tasks-check", str(ctx.exception))


class DetectTrackerTest(unittest.TestCase):
    def test_github(self) -> None:
        for url in ("git@github.com:o/r.git", "https://github.com/o/r", "https://github.com/o/r.git",
                    "ssh://git@github.com/o/r.git", "https://user:token@github.com/o/r", "https://www.github.com/o/r",
                    "git@GitHub.com:o/r.git"):
            with self.subTest(url=url):
                self.assertEqual(detect_tracker(url)[:2], ("github", "gh"))

    def test_gitlab(self) -> None:
        for url in ("git@gitlab.com:g/p.git", "https://gitlab.com/g/p", "git@gitlab.example.com:g/p.git",
                    "https://gitlab.mycorp.io/x/y.git", "ssh://git@code.gitlab.company.com:2222/x/y.git"):
            with self.subTest(url=url):
                self.assertEqual(detect_tracker(url)[:2], ("gitlab", "glab"))

    def test_anything_else_is_asked_about_and_names_the_host(self) -> None:
        for url, host in (("git@bitbucket.org:o/r.git", "bitbucket.org"), ("https://example.com/x/y", "example.com"),
                          ("git@github.mycorp.com:o/r.git", "github.mycorp.com"), ("git.company.com:o/r.git", "git.company.com")):
            with self.subTest(url=url):
                self.assertEqual(detect_tracker(url), (None, None, host))

    def test_a_url_without_a_host_is_a_usage_error(self) -> None:
        for bad in ("", "   ", "/just/a/path", "not a url at all"):
            with self.subTest(url=bad):
                with self.assertRaises(UsageError):
                    remote_host(bad)


class PlanExtraCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.skills = {}
        text = CONFIG
        for name in ("common", "glossary", "testing", "kotlin", "compose"):
            folder = self.dir / "skills" / name
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("---\nname: " + name + "\n---\n")
            text = text.replace("/skills/" + name + "/", str(folder) + "/")
            self.skills[name] = str(folder / "SKILL.md")
        self.config = self.dir / "config.md"
        self.config.write_text(text)
        self.tasks = self.dir / "tasks.md"
        self.tasks.write_text(TASKS)

    def test_brief_skills_prints_one_path_per_line(self) -> None:
        code, out, _ = run_tool(main, ["brief-skills", "--config", str(self.config), "--role", "implementer"])
        self.assertEqual((code, out), (0, "\n".join([self.skills["common"], self.skills["kotlin"], self.skills["compose"]]) + "\n"))

    def test_brief_skills_narrows_to_the_picks_of_one_task(self) -> None:
        self.tasks.write_text(TASKS.replace("Delivers:", "Skills: compose: the screen\nDelivers:", 1))
        args = ["brief-skills", "--config", str(self.config), "--role", "implementer", "--tasks", str(self.tasks)]
        code, out, _ = run_tool(main, args + ["--task", "t-1"])
        self.assertEqual((code, out), (0, self.skills["common"] + "\n" + self.skills["compose"] + "\n"))
        # a task without a Skills line gets the role's full list
        code, out, _ = run_tool(main, args + ["--task", "t-2"])
        self.assertEqual((code, out), (0, "\n".join([self.skills["common"], self.skills["kotlin"], self.skills["compose"]]) + "\n"))

    def test_brief_skills_needs_tasks_and_task_together(self) -> None:
        base = ["brief-skills", "--config", str(self.config), "--role", "implementer"]
        self.assertEqual(run_tool(main, base + ["--task", "t-1"])[0], 3)
        self.assertEqual(run_tool(main, base + ["--tasks", str(self.tasks)])[0], 3)
        self.assertEqual(run_tool(main, base + ["--tasks", str(self.tasks), "--task", "t-99"])[0], 1)

    def test_brief_skills_reads_the_extra_skills_from_the_state(self) -> None:
        state = self.dir / "state.md"
        state.write_text("# Story state\nstory: 2\nextra_skills: %s\n" % self.skills["glossary"])
        code, out, _ = run_tool(main, ["brief-skills", "--config", str(self.config), "--role", "story-reviewer", "--state", str(state)])
        self.assertEqual((code, out), (0, self.skills["common"] + "\n" + self.skills["glossary"] + "\n"))
        state.write_text("# Story state\nstory: 2\nextra_skills: none\n")
        self.assertEqual(run_tool(main, ["brief-skills", "--config", str(self.config), "--role", "story-reviewer", "--state", str(state)])[1], self.skills["common"] + "\n")

    def test_brief_skills_fails_hard_on_a_missing_file(self) -> None:
        Path(self.skills["kotlin"]).unlink()
        code, out, _ = run_tool(main, ["brief-skills", "--config", str(self.config), "--role", "implementer"])
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("error: "))
        self.assertIn(self.skills["kotlin"], out)

    def test_brief_skills_for_a_role_without_skills_prints_nothing(self) -> None:
        self.assertEqual(run_tool(main, ["brief-skills", "--config", str(self.config), "--role", "tester"]), (0, "", ""))

    def test_brief_skills_unknown_role_and_missing_options(self) -> None:
        self.assertEqual(run_tool(main, ["brief-skills", "--config", str(self.config), "--role", "janitor"])[0], 3)
        self.assertEqual(run_tool(main, ["brief-skills", "--config", str(self.config)])[0], 3)

    def test_issues_todo_prints_lines_and_exits_1_while_something_is_todo(self) -> None:
        code, out, _ = run_tool(main, ["issues-todo", "--tasks", str(self.tasks)], stdin=json.dumps(FACTS_EMPTY))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines(), IssuesTodoTest.ALL_TODO)

    def test_issues_todo_exits_0_when_everything_is_there(self) -> None:
        facts = {"issues": [{"number": 120, "title": "Story 2: Offline notes list"}]
                 + [{"number": 121 + i, "title": "t-%d: x" % (i + 1)} for i in range(4)],
                 "links": [{"blocked": "t-2", "by": "t-1"}, {"blocked": "t-3", "by": "t-1"},
                           {"blocked": "t-4", "by": "t-2"}, {"blocked": "t-4", "by": "t-3"}]}
        code, out, _ = run_tool(main, ["issues-todo", "--tasks", str(self.tasks)], stdin=json.dumps(facts))
        self.assertEqual(code, 0)
        self.assertTrue(all(line.startswith("have") for line in out.splitlines()))

    def test_issues_todo_bad_input(self) -> None:
        self.assertEqual(run_tool(main, ["issues-todo", "--tasks", str(self.tasks)], stdin="{nope")[0], 3)
        self.tasks.write_text("garbage")
        code, _, err = run_tool(main, ["issues-todo", "--tasks", str(self.tasks)], stdin="{}")
        self.assertEqual(code, 1)
        self.assertIn("tasks-check", err)

    def test_detect_tracker(self) -> None:
        self.assertEqual(run_tool(main, ["detect-tracker"], stdin="git@github.com:o/r.git\n"),
                         (0, "tracker: github\ntracker_cli: gh\n", ""))
        self.assertEqual(run_tool(main, ["detect-tracker"], stdin="https://gitlab.com/g/p\n")[1],
                         "tracker: gitlab\ntracker_cli: glab\n")

    def test_detect_tracker_asks_about_other_hosts(self) -> None:
        code, out, _ = run_tool(main, ["detect-tracker"], stdin="git@bitbucket.org:o/r.git\n")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("ask: bitbucket.org"))
        self.assertEqual(run_tool(main, ["detect-tracker"], stdin="\n")[0], 3)


if __name__ == "__main__":
    unittest.main()
