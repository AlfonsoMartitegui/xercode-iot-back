from __future__ import annotations

MISSING = object()


def get_path(value: object, path: str) -> object:
    current = value
    for part in _split_path(path):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]

    return current


def set_path(target: dict[str, object], path: str, value: object) -> None:
    current = target
    parts = _split_path(path)
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child

    current[parts[-1]] = value


def _split_path(path: str) -> list[str]:
    parts = [part.strip() for part in path.split(".") if part.strip()]
    if not parts:
        raise ValueError("Path cannot be empty")
    return parts
