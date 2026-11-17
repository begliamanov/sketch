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
        if not isinstance(value, str):
            return [path + " must be text"]
        if not value.strip():
            return [path + " must not be empty"]
        if not self.multiline and ("\n" in value or "\r" in value):
            return [path + " must be one line"]
        if self.choices and value not in self.choices:
            return [path + " must be one of " + ", ".join(self.choices) + " (got " + repr(value) + ")"]
        if self.pattern and not self.pattern.fullmatch(value):
            return [path + " must be " + self.pattern_hint + " (got " + repr(value) + ")"]
        return []


class Number(Spec):
    """A whole number of at least `minimum` (a boolean is not a number)."""

    def __init__(self, minimum: int = 0) -> None:
        self.minimum = minimum

    def check(self, value: Any, path: str) -> List[str]:
        if isinstance(value, bool) or not isinstance(value, int):
            return [path + " must be a whole number"]
        if value < self.minimum:
            return [path + " must be " + str(self.minimum) + " or more"]
        return []


class Items(Spec):
    """A list whose items all match `item`, with at least `minimum` items."""

    def __init__(self, item: Spec, minimum: int = 0) -> None:
        self.item = item
        self.minimum = minimum

    def check(self, value: Any, path: str) -> List[str]:
        if not isinstance(value, list):
            return [path + " must be a list"]
        problems: List[str] = []
        if len(value) < self.minimum:
            noun = "item" if self.minimum == 1 else "items"
            problems.append(path + " needs at least " + str(self.minimum) + " " + noun)
        for index, item in enumerate(value):
            problems.extend(self.item.check(item, path + "[" + str(index) + "]"))
        return problems


class Fields(Spec):
    """An object with known fields. Fields in `required` must be there, any other key is rejected."""

    def __init__(self, fields: Dict[str, Spec], required: Sequence[str] = ()) -> None:
        self.fields = fields
        self.required: Set[str] = set(required)

    def check(self, value: Any, path: str) -> List[str]:
        if not isinstance(value, dict):
            return [(path + " must be an object") if path else "the report must be an object"]
        problems: List[str] = []
        for key in self.fields:
            if key in self.required and key not in value:
                problems.append(join_path(path, key) + " is required")
        for key, spec in self.fields.items():
            if key in value:
                problems.extend(spec.check(value[key], join_path(path, key)))
        for key in value:
            if key not in self.fields:
                problems.append(join_path(path, str(key)) + " is not a field of this report")
        return problems


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
        if not isinstance(value, dict):
            return [path + " must be an object"]
        problems: List[str] = []
        if len(value) < self.minimum:
            noun = "entry" if self.minimum == 1 else "entries"
            problems.append(path + " needs at least " + str(self.minimum) + " " + noun)
        for key, item in value.items():
            if not isinstance(key, str) or not self.key_pattern.fullmatch(key):
                problems.append(path + " key " + repr(key) + " must be " + self.key_hint)
                continue
            problems.extend(self.value.check(item, join_path(path, key)))
        return problems


def join_path(path: str, key: str) -> str:
    """`a` + `b` -> `a.b`; the top level has an empty path."""
    return key if not path else path + "." + key
