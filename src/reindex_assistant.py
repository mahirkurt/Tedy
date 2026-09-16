#!/usr/bin/env python3
"""Manual reindex utility for TEDY assistant."""

import argparse
import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.assistant_core import AssistantRuntime  # noqa: E402
from src.env_loader import load_env  # noqa: E402


def main():
    load_env()
    parser = argparse.ArgumentParser(description="Reindex TEDY assistant knowledge base")
    parser.add_argument("--full", action="store_true", help="full rebuild instead of incremental")
    args = parser.parse_args()

    runtime = AssistantRuntime(PROJECT_ROOT)
    stats = runtime.reindex(incremental=not args.full)
    print("[Assistant] Reindex complete")
    for k in (
        "incremental",
        "files_indexed",
        "chunks_indexed",
        "changed_files",
        "unchanged_files",
        "deleted_files",
        "embedded_chunks",
        "duration_ms",
        "moduller",
    ):
        print(f"  {k}: {stats.get(k)}")


if __name__ == "__main__":
    main()
