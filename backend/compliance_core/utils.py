from __future__ import annotations

from typing import Any, Mapping

MISSING: object = object()


def get_in(data: Mapping[str, Any], dotted_path: str, default: Any = MISSING) -> Any:
    """
    Safely fetch a nested value using a dotted path like "a.b.c".
    Returns `default` if any part is missing or not a mapping.
    """
    current: Any = data
    for key in dotted_path.split("."):
        if not isinstance(current, Mapping):
            return default
        if key not in current:
            return default
        current = current[key]
    return current


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out

