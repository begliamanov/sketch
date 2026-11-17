"""guard: which shell commands must not run. Pure rules on the command text."""

import unittest
from typing import List, Tuple

from sketch_tools.guard.logic import check_command
from sketch_tools.guard.shellparse import simple_commands

PROTECTED = ["main", "master", "feature/offline-notes"]

ALLOWED = [
    "git status",
    "git log --oneline -5",
    "git diff main..feature/offline-notes",
    "git fetch origin main",
    "git checkout main",
    "git branch -D story-1-old",
    "git commit -m \"t-1: tests\"",
    "git commit -m \"push origin main and merge it\"",
    "git push -u origin story-2-offline-notes",
    "git push origin story-2-offline-notes",
    "git push -u origin HEAD:story-2-offline-notes",
    "git push origin refs/heads/story-2-x",
    "git push origin main-menu",
    "git push origin feature/offline-notes-extra",
    "git push origin v1.0.0",
    "git push origin refs/tags/v1.0.0",
    "git -C /tmp/repo push -u origin story-3",
    "gh pr create --base feature/offline-notes --title \"Story 2\" --body-file body.md",
    "gh pr view 5 --json baseRefName",
    "gh pr list --head story-2-x",
    "gh pr ready 5",
    "gh issue comment 3 --body \"done in PR #5\"",
    "gh issue list",
    "gh issue create --title x",
    "gh api repos/o/r/issues/3/comments",
    "glab mr view 5",
    "glab issue note 3 -m done",
    "echo \"git push --force origin main\"",
    "echo 'gh pr merge 5'",
    "grep -rn \"git merge\" docs/",
    "cat notes.md | grep -v 'gh issue close'",
    "ls; echo hi | grep x",
    "git add . && git commit -m wip && git push -u origin story-9",
    "git commit -m \"$(cat <<'EOF'\nt-1: add banner, don't break it\n\nCo-Authored-By: x\nEOF\n)\"",
    "cat > notes.md <<'EOF'\ngit push --force origin main\ngh pr merge 5\nEOF",
    "",
    "   ",
]

DENIED: List[Tuple[str, str]] = [
    # force pushes
    ("git push --force origin story-1", "force"),
    ("git push -f origin story-1", "force"),
    ("git push -fu origin story-1", "force"),
    ("git push --force-with-lease origin story-1", "force"),
    ("git push --force-with-lease=story-1 origin story-1", "force"),
    ("git push origin story-1 --force-if-includes", "force"),
    ("git push origin +story-1", "force"),
    ("git push origin +story-1:story-1", "force"),
    # protected branches
    ("git push origin main", "protected"),
    ("git push origin master", "protected"),
    ("git push -u origin main", "protected"),
    ("git push origin HEAD:main", "protected"),
    ("git push origin story-1:main", "protected"),
    ("git push origin refs/heads/main", "protected"),
    ("git push origin feature/offline-notes", "protected"),
    ("git push origin story-1 main", "protected"),
    # not explicit
    ("git push", "explicit branch"),
    ("git push origin", "explicit branch"),
    ("git push -u origin", "explicit branch"),
    ("git push origin HEAD", "explicit branch"),
    ("git push origin @", "explicit branch"),
    ("git push origin --tags", "explicit branch"),
    ("git push origin $BRANCH", "explicit branch"),
    ("git push origin \"$BRANCH\"", "explicit branch"),
    ("git push origin ${BRANCH}", "explicit branch"),
    ("BRANCH=main; git push origin $BRANCH", "explicit branch"),
    ("git push origin `git branch --show-current`", "explicit branch"),
    ("git push origin $(git branch --show-current)", "explicit branch"),
    # everything at once, deletions
    ("git push --all origin", "all"),
    ("git push --mirror origin", "all"),
    ("git push --prune origin story-1", "all"),
    ("git push origin --delete story-1", "delete"),
    ("git push -d origin story-1", "delete"),
    ("git push origin :story-1", "delete"),
    ("git push origin :main", "delete"),
    # wrappers and options in front
    ("/usr/bin/git push origin main", "protected"),
    ("env FOO=1 git push origin main", "protected"),
    ("FOO=1 BAR=2 git push --force origin story-1", "force"),
    ("sudo git push -f origin story-1", "force"),
    ("sudo -u root git push origin main", "protected"),
    ("command git push -f origin story-1", "force"),
    ("nohup git push origin main", "protected"),
    ("time git push origin main", "protected"),
    ("git -C repo push origin main", "protected"),
    ("git -c user.name=x push origin main", "protected"),
    ("git --git-dir=x/.git push origin main", "protected"),
    # chained, grouped, nested
    ("git add . && git push origin main", "protected"),
    ("echo hi; git push --force origin story-1", "force"),
    ("git status || git push -f origin story-1", "force"),
    ("echo hi\ngit push origin main", "protected"),
    ("(git push origin main)", "protected"),
    ("echo $(git push -f origin story-1)", "force"),
    ("echo `git push origin main`", "protected"),
    ("bash -c 'git push origin main'", "protected"),
    ("sh -c \"git push --force origin story-1\"", "force"),
    ("bash -lc 'cd x && git push origin main'", "protected"),
    ("eval \"git push -f origin story-1\"", "force"),
    ("bash <<'EOF'\ngit push origin main\nEOF", "protected"),
    ("git push origin main > /dev/null 2>&1", "protected"),
    # merging
    ("git merge story-1", "merge"),
    ("git merge --no-ff story-1", "merge"),
    ("git -C repo merge story-1", "merge"),
    ("gh pr merge 5", "merge"),
    ("gh pr merge 5 --squash --delete-branch", "merge"),
    ("gh pr merge -R o/r 5", "merge"),
    ("glab mr merge 5", "merge"),
    ("gh api -X PUT repos/o/r/pulls/5/merge", "merge"),
    ("gh api repos/o/r/pulls/5/merge -X PUT", "merge"),
    ("glab api projects/1/merge_requests/5/merge", "merge"),
    # closing issues
    ("gh issue close 5", "close"),
    ("glab issue close 5", "close"),
    ("gh issue close 5 --comment done", "close"),
    ("gh api -X PATCH repos/o/r/issues/5 -f state=closed", "close"),
    ("gh api repos/o/r/issues/5 --method PATCH -f state=closed", "close"),
    ("glab api -X PUT projects/1/issues/5 -f state_event=close", "close"),
]


class AllowedTest(unittest.TestCase):
    def test_these_commands_are_allowed(self) -> None:
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(check_command(command, PROTECTED), [])


class DeniedTest(unittest.TestCase):
    def test_these_commands_are_denied_for_the_right_reason(self) -> None:
        for command, needle in DENIED:
            with self.subTest(command=command):
                reasons = check_command(command, PROTECTED)
                self.assertTrue(reasons, "expected a denial")
                self.assertTrue(
                    any(needle in reason for reason in reasons),
                    "no reason containing %r in %r" % (needle, reasons),
                )

    def test_every_bad_part_of_a_command_is_reported(self) -> None:
        reasons = check_command("git push --force origin story-1 && gh pr merge 5 && gh issue close 3", PROTECTED)
        self.assertEqual(len(reasons), 3)

    def test_a_reason_says_what_to_do_instead_where_there_is_something(self) -> None:
        reasons = check_command("git push origin main", PROTECTED)
        self.assertIn("story branch", reasons[0])
        reasons = check_command("git push", PROTECTED)
        self.assertIn("git push -u origin <story-branch>", reasons[0])


class ProtectedBranchesTest(unittest.TestCase):
    def test_a_branch_is_protected_only_when_it_is_listed(self) -> None:
        self.assertEqual(check_command("git push origin main", []), [])
        self.assertNotEqual(check_command("git push origin main", ["main"]), [])
        self.assertEqual(check_command("git push origin develop", ["main"]), [])
        self.assertNotEqual(check_command("git push origin develop", ["main", "develop"]), [])

    def test_no_protected_branch_still_blocks_force_and_merge(self) -> None:
        self.assertNotEqual(check_command("git push -f origin story-1", []), [])
        self.assertNotEqual(check_command("gh pr merge 5", []), [])

    def test_push_block_refuses_every_push_with_its_reason(self) -> None:
        reasons = check_command("git push -u origin story-1", PROTECTED, push_block="no feature branch is known")
        self.assertEqual(len(reasons), 1)
        self.assertIn("no feature branch is known", reasons[0])
        self.assertEqual(check_command("git status", PROTECTED, push_block="no feature branch is known"), [])


class UnparseableTest(unittest.TestCase):
    def test_a_command_that_cannot_be_parsed_is_denied(self) -> None:
        reasons = check_command("git push origin main \"unterminated", PROTECTED)
        self.assertEqual(len(reasons), 1)
        self.assertIn("cannot parse", reasons[0])

    def test_an_unparseable_inner_part_is_skipped_not_denied(self) -> None:
        # an apostrophe inside a command substitution is common in commit messages
        self.assertEqual(check_command("echo \"$(echo don't)\"", PROTECTED), [])


class SimpleCommandsTest(unittest.TestCase):
    def test_splits_on_every_separator(self) -> None:
        self.assertEqual(
            simple_commands("a x; b y && c z || d w | e v\nf u"),
            [["a", "x"], ["b", "y"], ["c", "z"], ["d", "w"], ["e", "v"], ["f", "u"]],
        )

    def test_quotes_keep_words_together_and_hide_separators(self) -> None:
        self.assertEqual(simple_commands("echo 'a; b && c' \"d | e\""), [["echo", "a; b && c", "d | e"]])

    def test_wrappers_and_assignments_are_removed(self) -> None:
        self.assertEqual(simple_commands("FOO=1 env BAR=2 sudo -u root git status"), [["git", "status"]])
        self.assertEqual(simple_commands("/usr/bin/git log"), [["git", "log"]])

    def test_redirections_are_dropped(self) -> None:
        self.assertEqual(simple_commands("git log > out.txt 2>&1"), [["git", "log"]])

    def test_nested_commands_are_found_too(self) -> None:
        found = simple_commands("echo $(git status) && bash -c 'git log; git diff'")
        self.assertIn(["git", "status"], found)
        self.assertIn(["git", "log"], found)
        self.assertIn(["git", "diff"], found)

    def test_heredoc_bodies_are_data_unless_a_shell_reads_them(self) -> None:
        self.assertEqual(simple_commands("cat <<'EOF'\ngit push -f\nEOF"), [["cat"]])
        self.assertIn(["git", "push", "-f"], simple_commands("bash <<'EOF'\ngit push -f\nEOF"))

    def test_an_unterminated_quote_is_a_value_error(self) -> None:
        with self.assertRaises(ValueError):
            simple_commands("echo \"oops")


if __name__ == "__main__":
    unittest.main()
