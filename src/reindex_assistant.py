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
    summary_keys = (
        "incremental",
        "files_indexed",
        "chunks_indexed",
        "changed_files",
        "unchanged_files",
        "deleted_files",
        "embedded_chunks",
        "duration_ms",
    )
    print("[Assistant] Reindex complete")
    for k in summary_keys:
        print(f"  {k}: {stats.get(k)}")
    print(f"  moduller: {stats.get('moduller')}")
    _dusen_dosyalari_yazdir(stats)

    # Görev 5: content/pedagoji's own index, built by the same reindex() call —
    # own directory (output/assistant_index_aile), own summary, never folded
    # into the main index's numbers above.
    aile_stats = stats.get("aile_kaynagi") or {}
    print("[Assistant] Aile kaynağı reindex complete")
    for k in summary_keys:
        print(f"  {k}: {aile_stats.get(k)}")
    _dusen_dosyalari_yazdir(aile_stats)


def _dusen_dosyalari_yazdir(stats):
    """No silent drop (task-1 brief §2, "sessiz düşme yok"): AssistantIndexer
    .reindex() already names every chunk-cap-dropped file in `dusen_dosyalar`
    and logs a warning — this CLI summary must not swallow that by only
    printing the counters."""
    dusen = stats.get("dusen_dosyalar") or []
    nedenler = stats.get("dusen_dosyalar_nedenleri") or {}
    if dusen:
        etiketli = [f"{p} ({nedenler[p]})" if p in nedenler else p for p in dusen]
        print(f"  dusen_dosyalar ({len(dusen)}): {', '.join(etiketli)}")


if __name__ == "__main__":
    main()
