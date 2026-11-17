"""A small declarative validator for JSON reports: text, numbers, lists, objects, maps.

Every spec has `check(value, path)` and returns the problems it finds, one message each, with the
path of the field in it (`must_fix[1].evidence must not be empty`). Standard library only."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Pattern, Sequence, Set, Tuple


class Spec:
    """One kind of value."""

    def check(self, value: Any, path: str) -> List[str]:
        raise NotImplementedError


class Text(Spec):
    """A non-empty string: one line unless `multiline`, optionally one of `choices` or matching
    `pattern`."""

    def __init__(
        self, choices: Optional[Sequence[str]] = None, pattern: Optional[Pattern[str]] = None,
        pattern_hint: str = "", multiline: bool = False,
    ) -> None:
        self.choices = tuple(choices) if choices else None
        self.pattern = pattern
        self.pattern_hint = pattern_hint
        self.multiline = multiline

    def check(self, value: Any, path: str) -> List[str]:
        raise NotImplementedError


class Number(Spec):
    """A whole number of at least `minimum` (a boolean is not a number)."""

    def __init__(self, minimum: int = 0) -> None:
        self.minimum = minimum

    def check(self, value: Any, path: str) -> List[str]:
        raise NotImplementedError


class Items(Spec):
    """A list whose items all match `item`, with at least `minimum` items."""

    def __init__(self, item: Spec, minimum: int = 0) -> None:
        self.item = item
        self.minimum = minimum

    def check(self, value: Any, path: str) -> List[str]:
        raise NotImplementedError


class Fields(Spec):
    """An object with known fields. Fields in `required` must be there, any other key is rejected."""

    def __init__(self, fields: Dict[str, Spec], required: Sequence[str] = ()) -> None:
        self.fields = fields
        self.required: Set[str] = set(required)

    def check(self, value: Any, path: str) -> List[str]:
        raise NotImplementedError


class Mapping(Spec):
    """An object with any number of keys that match `key_pattern`, all values matching `value`."""

    def __init__(
        self, key_pattern: Pattern[str], key_hint: str, value: Spec, minimum: int = 0
    ) -> None:
        self.key_pattern = key_pattern
        self.key_hint = key_hint
        self.value = value
        self.minimum = minimum

    def check(self, value: Any, path: str) -> List[str]:
        raise NotImplementedError


def join_path(path: str, key: str) -> str:
    """`a` + `b` -> `a.b`; the top level has an empty path."""
    return key if not path else path + "." + key
