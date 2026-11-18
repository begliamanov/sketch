"""report: a story-end fix is reported on a story scope (story-<n>) by the test-writer and the
implementer; every other role keeps the scope kind it has."""

import unittest

from sketch_tools.core.errors import UsageError
from sketch_tools.report.logic import validate

from tests.report_examples import example


class StoryScopeAcceptedTest(unittest.TestCase):
    """Criteria 1 and 2: a story scope is accepted."""

    def test_a_test_writer_report_with_a_story_scope_is_accepted(self) -> None:
        self.assertEqual(validate("test-writer", "story-2", example("test-writer")), [])

    def test_an_implementer_report_with_a_story_scope_is_accepted(self) -> None:
        self.assertEqual(validate("implementer", "story-2", example("implementer")), [])

    def test_a_story_scope_needs_a_story_number(self) -> None:
        # addition: the story scope still has to look like story-<n>
        for role in ("test-writer", "implementer"):
            for bad in ("story", "story-", "story-x", "2"):
                with self.subTest(role=role, scope=bad):
                    with self.assertRaises(UsageError):
                        validate(role, bad, example(role))


class TaskScopeStillAcceptedTest(unittest.TestCase):
    """Criterion 3: both roles still accept a task scope."""

    def test_a_test_writer_report_with_a_task_scope_is_accepted(self) -> None:
        self.assertEqual(validate("test-writer", "t-3", example("test-writer")), [])

    def test_an_implementer_report_with_a_task_scope_is_accepted(self) -> None:
        self.assertEqual(validate("implementer", "t-3", example("implementer")), [])


class FixedScopeKindTest(unittest.TestCase):
    """Criterion 4: a role with a fixed scope kind refuses the other kind."""

    def test_a_reviewer_refuses_a_story_scope(self) -> None:
        with self.assertRaises(UsageError):
            validate("reviewer", "story-2", example("reviewer"))

    def test_story_only_roles_refuse_a_task_scope(self) -> None:
        for role in ("story-reviewer", "task-writer", "pr-agent", "retro-agent"):
            with self.subTest(role=role):
                with self.assertRaises(UsageError):
                    validate(role, "t-3", example(role))


if __name__ == "__main__":
    unittest.main()
