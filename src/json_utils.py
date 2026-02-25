"""Atomic JSON file operations."""
import json
import os


def atomic_json_dump(data, path, **kwargs):
    """Write JSON atomically: write to .tmp then rename.

    Prevents corrupted JSON from partial writes on crash.
    """
    kwargs.setdefault("indent", 2)
    kwargs.setdefault("ensure_ascii", False)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, **kwargs)
    os.replace(tmp, path)
