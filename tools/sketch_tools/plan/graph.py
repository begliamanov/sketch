"""A tiny dependency graph: cycle finding. Nodes are task ids like `t-3`."""

from __future__ import annotations

from typing import Dict, List, Optional


def task_number(task_id: str) -> int:
    """`t-12` -> 12. Task ids sort by number, never as text."""
    return int(task_id[2:])


def find_cycle(blocked_by: Dict[str, List[str]]) -> Optional[List[str]]:
    """The first dependency cycle, as a path that ends where it starts (`t-1 -> t-3 -> t-1`), or
    None. Starts from the lowest task number, so the answer is always the same. Edges to tasks that
    are not in the graph are ignored."""
    done: set = set()

    def visit(node: str, path: List[str]) -> Optional[List[str]]:
        if node in path:
            return path[path.index(node):] + [node]
        if node in done:
            return None
        path = path + [node]
        for blocker in sorted(blocked_by.get(node, []), key=task_number):
            if blocker in blocked_by:
                found = visit(blocker, path)
                if found:
                    return found
        done.add(node)
        return None

    for start in sorted(blocked_by, key=task_number):
        found = visit(start, [])
        if found:
            return found
    return None
