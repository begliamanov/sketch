"""The tests tool: run the project's tests once, and read their structured results (not their
console output) to answer: did it pass, what failed, did a new test fail first, was one skipped."""

from sketch_tools.tests.cli import main

__all__ = ["main"]
