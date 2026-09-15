"""Runtime settings for ted-mcp, read once from the environment (.env via load_env)."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from src.mcp_server.oauth_redirect import (EXTRA_FORM_ACTION_ORIGINS_ENV, EXTRA_REDIRECT_URIS_ENV,
                                           parse_extra_form_action_origins, parse_extra_redirect_uris)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_MAX_BODY_BYTES = 2_097_152

# Canonical fleet endpoints and the env var that carries each key (spec §7; plan K-P14, K-P30).
SERVER_DEFAULTS: dict[str, tuple[str, str]] = {
    "maarif-mufredat": ("https://mufredat.cureonics.com/mcp", "MUFREDAT_MCP_API_KEY"),
    "egitim-kaynak": ("https://egitim-kaynak.cureonics.com/mcp", "EGITIM_KAYNAK_MCP_API_KEY"),
    "anamnesis": ("https://anamnesis-mcp.cureonics.workers.dev/mcp", "ANAMNESIS_MCP_API_KEY"),
    "pexels": ("https://pexels-mcp.cureonics.workers.dev/mcp", "PEXELS_MCP_API_KEY"),
    "minimax": ("https://minimax-mcp.cureonics.workers.dev/mcp", "MINIMAX_MCP_API_KEY"),
    "comfyui": ("https://comfyui-mcp.cureonics.workers.dev/mcp", "COMFYUI_MCP_API_KEY"),
    # No public hostname; ted-mcp runs on the same host and tr-literatur accepts loopback + static bearer.
    "tr-literatur": ("http://127.0.0.1:8327/mcp", "TR_LITERATUR_MCP_API_KEY"),
    "openalex": ("https://openalex.cureonics.com/mcp", "OPENALEX_MCP_API_KEY"),
}
URL_ENV: dict[str, str] = {"tr-literatur": "TR_LITERATUR_MCP_URL"}


@dataclass(frozen=True)
class ServerConfig:
    name: str
    url: str
    api_key: str = field(repr=False)


@dataclass(frozen=True)
class Settings:
    public_base_url: str
    allowed_hosts: tuple[str, ...]
    data_dir: Path
    oauth_db_path: Path
    dashboard_api_url: str
    dashboard_api_key: str = field(repr=False)
    servers: dict[str, ServerConfig] = field(default_factory=dict)
    mcp_max_body_bytes: int = DEFAULT_MCP_MAX_BODY_BYTES
    extra_redirect_uris: tuple[str, ...] = ()
    extra_form_action_origins: tuple[str, ...] = ()
    dashboard_public_url: str = "https://tedy.online"
    parent_origin: str = "https://tedy.online"
    viewer_hosts: tuple[str, ...] = ("modul.tedy.online",)
    ticket_secret: bytes = field(default=b"", repr=False)
    media_monthly_usd: float = 10.0
    eric_api_url: str = "https://api.ies.ed.gov/eric/"


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    if not (raw.isascii() and raw.isdigit()) or int(raw) <= 0:
        raise ValueError(f"{name} must be a positive integer number of bytes, got {raw!r}")
    return int(raw)


def _money(raw: str | None, default: float) -> float:
    try:
        value = float(raw) if raw not in (None, "") else default
    except ValueError:
        return default
    if not math.isfinite(value):
        return default
    return max(0.0, value)


def load_settings(env: Mapping[str, str] | None = None, project_root: Path | None = None) -> Settings:
    env = os.environ if env is None else env
    root = PROJECT_ROOT if project_root is None else project_root
    base = (env.get("TED_MCP_PUBLIC_BASE_URL") or "https://mcp.tedy.online").strip().rstrip("/")
    hosts_raw = env.get("TED_MCP_ALLOWED_HOSTS") or base.split("://", 1)[-1].split("/", 1)[0]
    hosts = tuple(h.strip() for h in hosts_raw.split(",") if h.strip())
    viewer_raw = env.get("TED_MCP_VIEWER_HOSTS") or "modul.tedy.online"
    data_dir = root / "output"
    servers = {
        name: ServerConfig(name=name, url=(env.get(URL_ENV.get(name, "")) or url).strip(),
                           api_key=(env.get(key_env) or "").strip())
        for name, (url, key_env) in SERVER_DEFAULTS.items()
    }
    return Settings(
        public_base_url=base,
        allowed_hosts=hosts,
        data_dir=data_dir,
        oauth_db_path=data_dir / "ted_mcp_oauth.sqlite3",
        dashboard_api_url=(env.get("TED_DASHBOARD_API_URL") or "http://127.0.0.1:8085").rstrip("/"),
        dashboard_api_key=(env.get("TED_DASHBOARD_API_KEY") or "").strip(),
        servers=servers,
        mcp_max_body_bytes=_positive_int(env, "TED_MCP_MAX_BODY_BYTES", DEFAULT_MCP_MAX_BODY_BYTES),
        extra_redirect_uris=parse_extra_redirect_uris(env.get(EXTRA_REDIRECT_URIS_ENV)),
        extra_form_action_origins=parse_extra_form_action_origins(env.get(EXTRA_FORM_ACTION_ORIGINS_ENV)),
        dashboard_public_url=(env.get("TED_DASHBOARD_PUBLIC_URL") or "https://tedy.online").strip().rstrip("/"),
        parent_origin=(env.get("EDUPEDIA_PARENT_ORIGIN") or "https://tedy.online").strip().rstrip("/"),
        viewer_hosts=tuple(h.strip().lower() for h in viewer_raw.split(",") if h.strip()),
        ticket_secret=(env.get("EDUPEDIA_TICKET_SECRET") or "").encode("utf-8"),
        media_monthly_usd=_money(env.get("EDUPEDIA_MEDIA_MONTHLY_USD"), 10.0),
        eric_api_url=(env.get("EDUPEDIA_ERIC_API_URL") or "https://api.ies.ed.gov/eric/").strip(),
    )
