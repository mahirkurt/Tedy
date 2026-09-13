"""Runtime settings for ted-mcp, read once from the environment (.env via load_env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Canonical fleet endpoints and the env var that carries each key (spec §7).
SERVER_DEFAULTS: dict[str, tuple[str, str]] = {
    "maarif-mufredat": ("https://mufredat.cureonics.com/mcp", "MUFREDAT_MCP_API_KEY"),
    "egitim-kaynak": ("https://egitim-kaynak.cureonics.com/mcp", "EGITIM_KAYNAK_MCP_API_KEY"),
    "anamnesis": ("https://anamnesis-mcp.cureonics.workers.dev/mcp", "ANAMNESIS_MCP_API_KEY"),
}


@dataclass(frozen=True)
class ServerConfig:
    name: str
    url: str
    api_key: str


@dataclass(frozen=True)
class Settings:
    public_base_url: str
    allowed_hosts: tuple[str, ...]
    data_dir: Path
    oauth_db_path: Path
    dashboard_api_url: str
    dashboard_api_key: str
    servers: dict[str, ServerConfig] = field(default_factory=dict)


def load_settings(env: Mapping[str, str] | None = None, project_root: Path | None = None) -> Settings:
    env = os.environ if env is None else env
    root = PROJECT_ROOT if project_root is None else project_root
    base = (env.get("TED_MCP_PUBLIC_BASE_URL") or "https://mcp.tedy.online").strip().rstrip("/")
    hosts_raw = env.get("TED_MCP_ALLOWED_HOSTS") or base.split("://", 1)[-1].split("/", 1)[0]
    hosts = tuple(h.strip() for h in hosts_raw.split(",") if h.strip())
    data_dir = root / "output"
    servers = {
        name: ServerConfig(name=name, url=url, api_key=(env.get(key_env) or "").strip())
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
    )
