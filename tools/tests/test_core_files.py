"""The only file writers: atomic_write and append_text."""

import os
import tempfile
import unittest
from pathlib import Path

from sketch_tools.core.files import append_text, atomic_write


class AtomicWriteTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_creates_a_missing_file(self) -> None:
        path = self.dir / "state.md"
        atomic_write(path, "hello\n")
        self.assertEqual(path.read_text(), "hello\n")

    def test_replaces_existing_content_entirely(self) -> None:
        path = self.dir / "state.md"
        path.write_text("old content that is longer\n")
        atomic_write(path, "new\n")
        self.assertEqual(path.read_text(), "new\n")

    def test_leaves_no_temp_files_behind(self) -> None:
        path = self.dir / "state.md"
        atomic_write(path, "x\n")
        self.assertEqual(os.listdir(self.dir), ["state.md"])

    def test_keeps_original_when_the_write_cannot_happen(self) -> None:
        path = self.dir / "state.md"
        path.write_text("original\n")
        missing_dir_target = self.dir / "no-such-dir" / "state.md"
        with self.assertRaises(OSError):
            atomic_write(missing_dir_target, "x\n")
        self.assertEqual(path.read_text(), "original\n")


class AppendTextTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_creates_a_missing_file(self) -> None:
        path = self.dir / "journal.md"
        append_text(path, "one\n")
        self.assertEqual(path.read_text(), "one\n")

    def test_appends_after_existing_content_without_changing_it(self) -> None:
        path = self.dir / "journal.md"
        path.write_text("first\nsecond\n")
        append_text(path, "third\n")
        self.assertEqual(path.read_text(), "first\nsecond\nthird\n")

    def test_raises_when_the_directory_is_missing(self) -> None:
        with self.assertRaises(OSError):
            append_text(self.dir / "no-such-dir" / "journal.md", "x\n")


if __name__ == "__main__":
    unittest.main()
