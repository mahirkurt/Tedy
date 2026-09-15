"""Live, cost-free fleet contract probe for ted-mcp (plan Task 21 Step 7).

Calls tools/list on every configured fleet server and GETs one ERIC record. Never calls a tool,
so nothing is billed. Prints only server names and results — never keys.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from src.env_loader import load_env  # noqa: E402
from src.mcp_client import McpClient  # noqa: E402
from src.mcp_server.config import load_settings  # noqa: E402

BEKLENEN: dict[str, set[str]] = {
    "maarif-mufredat": {"list_subjects", "search_learning_outcomes", "list_textbooks", "get_document_text",
                        "search_figures", "get_figure"},
    "egitim-kaynak": {"kb_search", "kb_for_outcome"},
    "anamnesis": {"ingest_document", "hybrid_query"},
    "pexels": {"search_photos"},
    "minimax": {"text_to_audio", "text_to_image", "music_generation", "generate_video", "query_video_generation",
                "list_voices"},
    "comfyui": {"generate_song", "wan_i2v", "get_job"},
    "tr-literatur": {"tr_literatur_search_articles", "tr_literatur_server_info"},
    "openalex": {"openalex_search_entities"},
}


def eksikler(listed: list[dict], beklenen: set[str]) -> list[str]:
    return sorted(beklenen - {t.get("name") for t in listed if isinstance(t, dict)})


def eric_yokla(session, url: str) -> str:
    try:
        response = session.get(url, params={"search": "retrieval practice", "format": "json", "rows": 1}, timeout=25)
        docs = (response.json().get("response") or {}).get("docs")
    except (requests.RequestException, ValueError, AttributeError) as exc:
        return f"hata: {type(exc).__name__}"
    if response.status_code != 200 or not isinstance(docs, list):
        return f"hata: http_{response.status_code}"
    return "ok"


def yokla(settings, client_factory=McpClient, session=None) -> dict[str, str]:
    results: dict[str, str] = {}
    for name, expected in BEKLENEN.items():
        cfg = settings.servers[name]
        if not cfg.api_key:
            results[name] = "anahtar yok"
            continue
        tools = client_factory(name=cfg.name, url=cfg.url, api_key=cfg.api_key).list_tools()
        if not tools:
            results[name] = "hata: tools/list boş veya erişilemedi"
            continue
        missing = eksikler(tools, expected)
        results[name] = "ok" if not missing else "eksik: " + ", ".join(missing)
    results["eric"] = eric_yokla(session if session is not None else requests.Session(), settings.eric_api_url)
    return results


def main() -> int:
    load_env()
    results = yokla(load_settings())
    for name, result in results.items():
        print(f"{name}: {result}")
    return 0 if all(r in ("ok", "anahtar yok") for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
