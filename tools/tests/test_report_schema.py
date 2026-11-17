"""report: the schema primitives, on plain values."""

import re
import unittest

from sketch_tools.report.schema import Fields, Items, Mapping, Number, Text, join_path


class TextTest(unittest.TestCase):
    def test_a_one_line_string_is_fine(self) -> None:
        self.assertEqual(Text().check("hello there", "x"), [])
        self.assertEqual(Text().check("  keep spacing  ", "x"), [])

    def test_empty_and_wrong_types_are_reported_with_the_path(self) -> None:
        self.assertEqual(Text().check("", "a.b"), ["a.b must not be empty"])
        self.assertEqual(Text().check("   ", "a.b"), ["a.b must not be empty"])
        for bad in (5, None, ["x"], {"a": 1}, True):
            with self.subTest(value=bad):
                self.assertEqual(Text().check(bad, "x"), ["x must be text"])

    def test_a_second_line_is_rejected_unless_multiline(self) -> None:
        self.assertEqual(Text().check("a\nb", "x"), ["x must be one line"])
        self.assertEqual(Text(multiline=True).check("a\nb", "x"), [])

    def test_choices(self) -> None:
        spec = Text(choices=["SATISFIED", "CHANGES NEEDED"])
        self.assertEqual(spec.check("SATISFIED", "verdict"), [])
        problems = spec.check("maybe", "verdict")
        self.assertEqual(len(problems), 1)
        self.assertIn("verdict must be one of SATISFIED, CHANGES NEEDED", problems[0])
        self.assertIn("'maybe'", problems[0])

    def test_pattern_with_its_hint(self) -> None:
        spec = Text(pattern=re.compile(r"t-\d+"), pattern_hint="like t-3")
        self.assertEqual(spec.check("t-3", "id"), [])
        self.assertEqual(spec.check("t3", "id"), ["id must be like t-3 (got 't3')"])


class NumberTest(unittest.TestCase):
    def test_whole_numbers(self) -> None:
        self.assertEqual(Number().check(0, "n"), [])
        self.assertEqual(Number().check(42, "n"), [])

    def test_not_numbers(self) -> None:
        for bad in ("42", 4.5, None, True, [1]):
            with self.subTest(value=bad):
                self.assertEqual(Number().check(bad, "n"), ["n must be a whole number"])

    def test_the_minimum(self) -> None:
        self.assertEqual(Number(minimum=1).check(1, "n"), [])
        self.assertEqual(Number(minimum=1).check(0, "n"), ["n must be 1 or more"])
        self.assertEqual(Number().check(-1, "n"), ["n must be 0 or more"])


class ItemsTest(unittest.TestCase):
    def test_a_list_of_valid_items(self) -> None:
        self.assertEqual(Items(Text()).check(["a", "b"], "x"), [])
        self.assertEqual(Items(Text()).check([], "x"), [])

    def test_not_a_list(self) -> None:
        for bad in ("a", None, {"a": 1}, 5):
            with self.subTest(value=bad):
                self.assertEqual(Items(Text()).check(bad, "x"), ["x must be a list"])

    def test_the_minimum(self) -> None:
        self.assertEqual(Items(Text(), minimum=1).check([], "x"), ["x needs at least 1 item"])
        self.assertEqual(Items(Text(), minimum=2).check(["a"], "x"), ["x needs at least 2 items"])

    def test_each_bad_item_is_reported_with_its_index(self) -> None:
        self.assertEqual(
            Items(Text()).check(["ok", "", 5], "must_fix"),
            ["must_fix[1] must not be empty", "must_fix[2] must be text"],
        )


class FieldsTest(unittest.TestCase):
    SPEC = Fields({"name": Text(), "count": Number(), "tags": Items(Text())}, required=["name", "count"])

    def test_a_valid_object(self) -> None:
        self.assertEqual(self.SPEC.check({"name": "a", "count": 1}, ""), [])
        self.assertEqual(self.SPEC.check({"name": "a", "count": 1, "tags": ["x"]}, ""), [])

    def test_not_an_object(self) -> None:
        self.assertEqual(self.SPEC.check([1], "x"), ["x must be an object"])
        self.assertEqual(self.SPEC.check(None, ""), ["the report must be an object"])

    def test_missing_required_fields_are_named(self) -> None:
        self.assertEqual(self.SPEC.check({"name": "a"}, ""), ["count is required"])
        self.assertEqual(self.SPEC.check({}, "obj"), ["obj.name is required", "obj.count is required"])

    def test_unknown_fields_are_rejected(self) -> None:
        self.assertEqual(self.SPEC.check({"name": "a", "count": 1, "colour": "red"}, ""),
                         ["colour is not a field of this report"])

    def test_nested_problems_carry_the_whole_path(self) -> None:
        self.assertEqual(self.SPEC.check({"name": "", "count": "1", "tags": [""]}, ""),
                         ["name must not be empty", "count must be a whole number", "tags[0] must not be empty"])

    def test_nested_objects(self) -> None:
        outer = Fields({"inner": Fields({"id": Text()}, required=["id"])}, required=["inner"])
        self.assertEqual(outer.check({"inner": {}}, ""), ["inner.id is required"])


class MappingTest(unittest.TestCase):
    SPEC = Mapping(re.compile(r"t-\d+"), "like t-3", Number(minimum=1), minimum=1)

    def test_a_valid_mapping(self) -> None:
        self.assertEqual(self.SPEC.check({"t-1": 121, "t-2": 122}, "task_issues"), [])

    def test_bad_keys_and_values_and_size(self) -> None:
        self.assertEqual(self.SPEC.check({"x": 1}, "m"), ["m key 'x' must be like t-3"])
        self.assertEqual(self.SPEC.check({"t-1": 0}, "m"), ["m.t-1 must be 1 or more"])
        self.assertEqual(self.SPEC.check({}, "m"), ["m needs at least 1 entry"])
        self.assertEqual(self.SPEC.check([1], "m"), ["m must be an object"])


class JoinPathTest(unittest.TestCase):
    def test_join(self) -> None:
        self.assertEqual(join_path("", "a"), "a")
        self.assertEqual(join_path("a", "b"), "a.b")


if __name__ == "__main__":
    unittest.main()
