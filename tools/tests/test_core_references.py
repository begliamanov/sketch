"""The docs in core/ must call real tools: every `{{TOOLS}}/sketch-...` command they show exists,
and the old drift-notetaker agent is gone."""

import importlib
import re
import unittest
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
CALL = re.compile(r"\{\{TOOLS\}\}/sketch-([a-z-]+)((?: [a-z][a-z-]*){0,2})([^`\n]*)")


def core_files() -> List[Path]:
    return sorted((ROOT / "core").rglob("*.md"))


def calls() -> List[Tuple[Path, str, List[str], str]]:
    """Every tool call written in core/: (file, tool, leading words, rest of the line)."""
    found = []
    for path in core_files():
        for match in CALL.finditer(path.read_text()):
            found.append((path, match.group(1), match.group(2).split(), match.group(3)))
    return found


class CoreCallsRealToolsTest(unittest.TestCase):
    def test_the_docs_actually_use_the_tools(self) -> None:
        self.assertGreaterEqual(len(calls()), 15)

    def test_every_call_names_an_existing_tool_and_command(self) -> None:
        for path, tool_name, words, _rest in calls():
            with self.subTest(file=path.name, call=tool_name + " " + " ".join(words)):
                module = importlib.import_module(
                    "sketch_tools." + tool_name.replace("-", "_") + ".cli"
                )
                names = module.build_tool().command_names()
                one = words[0] if words else ""
                two = " ".join(words[:2])
                self.assertTrue(one in names or two in names, "no command %r in %r" % (words, names))

    def test_a_call_always_points_the_tool_at_its_file(self) -> None:
        needs = {"state": "--state", "journal": "--journal", "report": "--reports"}
        for path, tool_name, words, rest in calls():
            if tool_name in needs:
                with self.subTest(file=path.name, call=tool_name + " " + " ".join(words)):
                    self.assertIn(needs[tool_name], rest)


class ReportsAreHandedInThroughTheToolTest(unittest.TestCase):
    def test_every_agent_tells_the_agent_to_submit_its_report_with_its_own_role(self) -> None:
        from tests.report_examples import EXAMPLES

        for role in EXAMPLES:
            with self.subTest(role=role):
                text = (ROOT / "core" / "agents" / (role + ".md")).read_text()
                self.assertIn("sketch-report submit", text)
                self.assertIn("--role " + role, text)

    def test_the_orchestrator_checks_reports_and_reads_fields_from_them(self) -> None:
        orchestrator = (ROOT / "core" / "orchestrator.md").read_text()
        self.assertIn("sketch-report check", orchestrator)
        run_story = (ROOT / "core" / "skills" / "run-story" / "SKILL.md").read_text()
        self.assertIn("sketch-report check", run_story)
        self.assertIn("sketch-report get", run_story)


class SkillsUseTheReadingToolsTest(unittest.TestCase):
    """The skills that used to work these answers out by eye now ask the tools."""

    WIRED = {
        "sketch": ("sketch-state gate", "sketch-journal signals"),
        "retro": ("sketch-journal me-lines",),
        "resume-story": ("sketch-state reconcile",),
        "pause": ("sketch-state wip-message",),
        "stop": ("sketch-state wip-message",),
    }

    def test_each_skill_calls_its_tool(self) -> None:
        for skill, needles in self.WIRED.items():
            text = (ROOT / "core" / "skills" / skill / "SKILL.md").read_text()
            for needle in needles:
                with self.subTest(skill=skill, tool=needle):
                    self.assertIn(needle, text)


class DriftNotetakerIsGoneTest(unittest.TestCase):
    def test_the_agent_file_is_deleted(self) -> None:
        self.assertFalse((ROOT / "core" / "agents" / "drift-notetaker.md").exists())

    def test_nothing_mentions_it_any_more(self) -> None:
        places = [ROOT / "core", ROOT / "adapters", ROOT / "README.md"]
        for place in places:
            files = [place] if place.is_file() else [p for p in place.rglob("*") if p.is_file()]
            for path in files:
                with self.subTest(file=str(path.relative_to(ROOT))):
                    self.assertNotIn("drift-notetaker", path.read_text(errors="ignore"))


if __name__ == "__main__":
    unittest.main()
