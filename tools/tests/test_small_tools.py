"""skills list, setup check and retro recommend."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

from sketch_tools.core.errors import UsageError
from sketch_tools.retro import main as retro_main
from sketch_tools.retro.logic import recommend
from sketch_tools.setup import main as setup_main
from sketch_tools.setup.logic import missing_steps, parse_facts
from sketch_tools.skills import main as skills_main
from sketch_tools.skills.logic import Skill, parse_skill

from tests.helpers import run_tool


class ParseSkillTest(unittest.TestCase):
    def test_name_and_description_from_the_front_matter(self) -> None:
        text = "---\nname: kotlin\ndescription: Kotlin style rules.\n---\n\nbody text\n"
        self.assertEqual(parse_skill("/s/kotlin/SKILL.md", text), Skill("kotlin", "Kotlin style rules.", "/s/kotlin/SKILL.md"))

    def test_quotes_are_removed_and_a_colon_inside_is_kept(self) -> None:
        text = '---\nname: "sketch"\ndescription: "Starts a story. Usage - /sketch <idea>: go."\n---\n'
        skill = parse_skill("/s/sketch/SKILL.md", text)
        self.assertEqual((skill.name, skill.description), ("sketch", "Starts a story. Usage - /sketch <idea>: go."))
        text = "---\nname: x\ndescription: 'single quoted'\n---\n"
        self.assertEqual(parse_skill("/s/x/SKILL.md", text).description, "single quoted")

    def test_a_folded_description_is_joined_into_one_line(self) -> None:
        text = "---\nname: x\ndescription: >\n  line one\n  line two\nother: y\n---\n"
        self.assertEqual(parse_skill("/s/x/SKILL.md", text).description, "line one line two")
        text = "---\nname: x\ndescription: first part\n  second part\n---\n"
        self.assertEqual(parse_skill("/s/x/SKILL.md", text).description, "first part second part")

    def test_without_front_matter_or_a_name_the_folder_name_is_used(self) -> None:
        self.assertEqual(parse_skill("/s/folder-name/SKILL.md", "just text\n"), Skill("folder-name", "", "/s/folder-name/SKILL.md"))
        self.assertEqual(parse_skill("/s/folder-name/SKILL.md", "---\ndescription: d\n---\n").name, "folder-name")

    def test_a_dash_line_in_the_body_is_not_front_matter(self) -> None:
        text = "---\nname: x\n---\nbody\n---\nname: not-this\n---\n"
        self.assertEqual(parse_skill("/s/x/SKILL.md", text).name, "x")


class SkillsCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def skill(self, relative: str, name: str, description: str) -> Path:
        path = self.root / relative / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: %s\ndescription: %s\n---\nbody\n" % (name, description))
        return path

    def test_lists_every_skill_file_sorted_by_name_as_tab_separated_lines(self) -> None:
        b = self.skill("skills/b", "bravo", "The second one.")
        a = self.skill("deep/plugin/1.0/skills/a", "alpha", "The first one.")
        code, out, err = run_tool(skills_main, ["list", "--dir", str(self.root)])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "alpha\t%s\tThe first one.\nbravo\t%s\tThe second one.\n" % (a, b))

    def test_hidden_and_vendored_folders_are_not_searched(self) -> None:
        self.skill("good", "good", "d")
        self.skill(".git/hooks", "hidden", "d")
        self.skill("node_modules/pkg", "vendored", "d")
        self.skill("__pycache__/x", "cache", "d")
        _, out, _ = run_tool(skills_main, ["list", "--dir", str(self.root)])
        self.assertEqual([line.split("\t")[0] for line in out.splitlines()], ["good"])

    def test_several_dirs_and_json(self) -> None:
        one, two = self.root / "one", self.root / "two"
        self.skill("one/a", "a", "da")
        self.skill("two/b", "b", "db")
        code, out, _ = run_tool(skills_main, ["list", "--dir", str(one), "--dir", str(two), "--json"])
        data = json.loads(out)
        self.assertEqual((code, [s["name"] for s in data]), (0, ["a", "b"]))
        self.assertEqual(set(data[0]), {"name", "description", "path"})

    def test_the_same_skill_found_twice_is_listed_once(self) -> None:
        self.skill("a", "a", "d")
        _, out, _ = run_tool(skills_main, ["list", "--dir", str(self.root), "--dir", str(self.root / "a")])
        self.assertEqual(len(out.splitlines()), 1)

    def test_a_dir_without_skills_prints_nothing_and_a_missing_dir_exits_3(self) -> None:
        self.assertEqual(run_tool(skills_main, ["list", "--dir", str(self.root)]), (0, "", ""))
        code, out, err = run_tool(skills_main, ["list", "--dir", str(self.root / "nope")])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("nope", err)

    def test_at_least_one_dir_is_required(self) -> None:
        code, _, err = run_tool(skills_main, ["list"])
        self.assertEqual(code, 3)
        self.assertIn("--dir", err)

    def test_the_description_has_no_tabs_or_newlines_so_the_columns_stay_whole(self) -> None:
        path = self.root / "t" / "SKILL.md"
        path.parent.mkdir()
        path.write_text("---\nname: t\ndescription: a\tb\n---\n")
        _, out, _ = run_tool(skills_main, ["list", "--dir", str(self.root)])
        self.assertEqual(len(out.splitlines()), 1)
        self.assertEqual(len(out.splitlines()[0].split("\t")), 3)


GOOD_FACTS: Dict[str, Any] = {
    "git_repo": True, "has_commit": True, "has_remote": True, "cli_logged_in": True, "tracker_cli": "gh",
    "sketch_dir": True, "sketch_excluded": True, "has_config": True, "has_docs": True,
    "on_default_branch": False, "feature_pushed": True,
}


class SetupCheckTest(unittest.TestCase):
    def facts(self, **changes: Any) -> Dict[str, Any]:
        return dict(GOOD_FACTS, **changes)

    def test_nothing_missing(self) -> None:
        self.assertEqual(missing_steps(GOOD_FACTS), [])
        self.assertEqual(missing_steps({}), [])

    def test_each_missing_thing_has_its_kind_and_its_exact_command(self) -> None:
        cases = {
            "git_repo": ("safe", "git init"),
            "has_commit": ("safe", 'git add -A && git commit -m "Initial commit"'),
            "has_remote": ("ask", "gh repo create <name> --private --source=. --remote=origin (the developer names it and picks the visibility)"),
            "cli_logged_in": ("yours", "gh auth login"),
            "sketch_dir": ("safe", "mkdir -p .sketch/logs .sketch/retro .sketch/reports"),
            "sketch_excluded": ("safe", 'echo ".sketch/" >> .git/info/exclude'),
            "has_config": ("yours", "run /tune-skills"),
            "has_docs": ("safe", "mkdir -p docs/adr"),
            "feature_pushed": ("ask", "git push -u origin <feature-branch> (only during /sketch, the first and only push to it)"),
        }
        for key, expected in cases.items():
            with self.subTest(fact=key):
                self.assertEqual(missing_steps(self.facts(**{key: False})), [expected])

    def test_being_on_the_default_branch_needs_a_feature_branch(self) -> None:
        self.assertEqual(
            missing_steps(self.facts(on_default_branch=True)),
            [("ask", "git switch -c feature/<name> (a name the developer agrees to)")],
        )

    def test_gitlab_commands(self) -> None:
        steps = missing_steps(self.facts(tracker_cli="glab", has_remote=False, cli_logged_in=False))
        self.assertEqual(steps[0], ("ask", "glab repo create <name> --private (the developer names it and picks the visibility)"))
        self.assertEqual(steps[1], ("yours", "glab auth login"))

    def test_the_default_tracker_cli_is_gh(self) -> None:
        facts = {k: v for k, v in self.facts(cli_logged_in=False).items() if k != "tracker_cli"}
        self.assertEqual(missing_steps(facts), [("yours", "gh auth login")])

    def test_everything_missing_comes_in_the_order_to_do_it(self) -> None:
        facts = {key: False for key in GOOD_FACTS if key not in ("tracker_cli", "on_default_branch")}
        facts["on_default_branch"] = True
        facts["tracker_cli"] = "gh"
        texts = [text for _, text in missing_steps(facts)]
        self.assertEqual(len(texts), 10)
        starts = ["git init", "git add -A", "gh repo create", "gh auth login", "mkdir -p .sketch", 'echo ".sketch/"',
                  "run /tune-skills", "mkdir -p docs", "git switch -c", "git push -u"]
        for text, start in zip(texts, starts):
            self.assertTrue(text.startswith(start), (text, start))

    def test_facts_must_be_valid(self) -> None:
        self.assertEqual(parse_facts(json.dumps(GOOD_FACTS)), GOOD_FACTS)
        self.assertEqual(parse_facts("{}"), {})
        for text, needle in (
            ("{nope", "JSON"), ("[1]", "object"), (json.dumps({"git_rpo": False}), "git_rpo"),
            (json.dumps({"git_repo": "no"}), "true or false"), (json.dumps({"tracker_cli": "hub"}), "gh or glab"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(UsageError) as ctx:
                    parse_facts(text)
                self.assertIn(needle, str(ctx.exception))


class SetupCliTest(unittest.TestCase):
    def test_nothing_missing_prints_ok(self) -> None:
        self.assertEqual(run_tool(setup_main, ["check"], stdin=json.dumps(GOOD_FACTS)), (0, "ok\n", ""))

    def test_missing_steps_are_numbered_and_exit_1(self) -> None:
        facts = dict(GOOD_FACTS, git_repo=False, cli_logged_in=False, has_config=False)
        code, out, _ = run_tool(setup_main, ["check"], stdin=json.dumps(facts))
        self.assertEqual(code, 1)
        self.assertEqual(out, "1. safe: git init\n2. yours: gh auth login\n3. yours: run /tune-skills\n")

    def test_bad_facts_exit_3(self) -> None:
        self.assertEqual(run_tool(setup_main, ["check"], stdin="{nope")[0], 3)


class RecommendTest(unittest.TestCase):
    def rec(self, story: int = 5, flags: int = 0, caps: int = 0, lines: int = 0, comments: int = 0):
        return recommend(story, flags, caps, lines, comments)

    def test_nothing_notable(self) -> None:
        self.assertEqual(self.rec(), [])

    def test_the_first_three_stories_always_get_one(self) -> None:
        for story in (1, 2, 3):
            self.assertEqual(self.rec(story=story), ["story %d is one of the first 3" % story])
        self.assertEqual(self.rec(story=4), [])

    def test_flags_and_cap_hits(self) -> None:
        self.assertEqual(self.rec(flags=1), ["1 flagged task"])
        self.assertEqual(self.rec(flags=2), ["2 flagged tasks"])
        self.assertEqual(self.rec(caps=1), ["1 cap hit"])
        self.assertEqual(self.rec(caps=3), ["3 cap hits"])

    def test_the_limits_are_more_than_not_at_least(self) -> None:
        self.assertEqual(self.rec(lines=20, comments=10), [])
        self.assertEqual(self.rec(lines=21), ["you changed 21 lines after the PR (more than 20)"])
        self.assertEqual(self.rec(comments=11), ["11 review comments (more than 10)"])

    def test_every_reason_is_listed_in_one_pass(self) -> None:
        self.assertEqual(len(self.rec(story=1, flags=1, caps=1, lines=50, comments=50)), 5)

    def test_the_limits_can_be_changed(self) -> None:
        self.assertEqual(recommend(5, 0, 0, 30, 0, max_lines=50), [])
        self.assertEqual(recommend(5, 0, 0, 0, 5, max_comments=3), ["5 review comments (more than 3)"])
        self.assertEqual(recommend(5, 0, 0, 0, 0, first_stories=5), ["story 5 is one of the first 5"])

    def test_bad_numbers_are_usage_errors(self) -> None:
        for kwargs in ({"story": 0}, {"flags": -1}, {"caps": -1}, {"lines": -1}, {"comments": -1}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(UsageError):
                    self.rec(**kwargs)


class RecommendCliTest(unittest.TestCase):
    ARGS = ["recommend", "--story", "5", "--flags", "0", "--caps", "0", "--lines-changed", "0", "--comments", "0"]

    def test_not_notable(self) -> None:
        self.assertEqual(run_tool(retro_main, self.ARGS), (0, "not notable\n", ""))

    def test_recommended_with_its_reasons(self) -> None:
        argv = ["recommend", "--story", "2", "--flags", "2", "--caps", "0", "--lines-changed", "30", "--comments", "0"]
        self.assertEqual(
            run_tool(retro_main, argv),
            (0, "recommended\nreason: story 2 is one of the first 3\nreason: 2 flagged tasks\n"
                "reason: you changed 30 lines after the PR (more than 20)\n", ""),
        )

    def test_limit_options(self) -> None:
        argv = self.ARGS[:-1] + ["8", "--max-comments", "5"]
        self.assertEqual(run_tool(retro_main, argv)[1], "recommended\nreason: 8 review comments (more than 5)\n")

    def test_every_count_is_required_and_must_be_a_number(self) -> None:
        for missing in ("--story", "--flags", "--caps", "--lines-changed", "--comments"):
            with self.subTest(missing=missing):
                argv = list(self.ARGS)
                index = argv.index(missing)
                del argv[index:index + 2]
                self.assertEqual(run_tool(retro_main, argv)[0], 3)
        self.assertEqual(run_tool(retro_main, self.ARGS[:2] + ["x"] + self.ARGS[3:])[0], 3)
        self.assertEqual(run_tool(retro_main, ["recommend", "--story", "5", "--flags", "-1", "--caps", "0",
                                               "--lines-changed", "0", "--comments", "0"])[0], 3)


if __name__ == "__main__":
    unittest.main()
