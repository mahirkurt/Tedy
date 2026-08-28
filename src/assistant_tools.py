"""Tool registry for the assistant's function-calling loop.

Declarations are built from each server's own inputSchema rather than written
by hand. That is not a style preference: search_learning_outcomes takes `q`
(not `query`), wants `grade` as a string, and only its description says the
canonical form is "5.Sınıf". Measured — a hand-written declaration produced
grade:"6"; the server's schema, descriptions intact, produced grade:"5.Sınıf".
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from src.mcp_client import McpClient, McpToolResult

logger = logging.getLogger(__name__)

# Gemini-facing name -> (server, MCP tool name).
# Ten of the 27 available tools. The rest are not exposed because a large tool
# list bloats every prompt and slows the loop; adding one is a single line.
TOOL_ALLOWLIST: dict[str, tuple[str, str]] = {
    "kazanim_ara":       ("maarif-mufredat", "search_learning_outcomes"),
    "kazanim_listele":   ("maarif-mufredat", "list_learning_outcomes"),
    "mufredat_ara":      ("maarif-mufredat", "search"),
    "kitap_listele":     ("maarif-mufredat", "list_textbooks"),
    "kitap_sayfa":       ("maarif-mufredat", "get_document_text"),
    "figur_ara":         ("maarif-mufredat", "search_figures"),
    "figur_getir":       ("maarif-mufredat", "get_figure"),
    "oer_ara":           ("egitim-kaynak", "kb_search"),
    "oer_kazanima_gore": ("egitim-kaynak", "kb_for_outcome"),
}

# Which citation class a server's output belongs to. The distinction is load
# bearing: local files are authoritative for Işık's own data, the curriculum
# server for subject knowledge, and the two must never be blended.
_KIND_BY_TOOL: dict[str, str] = {
    "kitap_sayfa": "kitap",
    "figur_ara": "kitap",
    "figur_getir": "kitap",
    "oer_ara": "oer",
    "oer_kazanima_gore": "oer",
}

LOCAL_TOOL = "ogrenci_verisi_ara"

MCP_SERVERS = {
    "maarif-mufredat": ("https://mufredat.cureonics.com/mcp",
                        "MUFREDAT_MCP_API_KEY"),
    "egitim-kaynak": ("https://egitim-kaynak.cureonics.com/mcp",
                      "EGITIM_KAYNAK_MCP_API_KEY"),
}


@dataclass
class ToolOutcome:
    ok: bool
    text: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """MCP inputSchema -> a declaration parameter block.

    The installed google-genai accepts the raw Pydantic schema today, so this
    is a sanitiser rather than a rewriter: it drops `title` noise and collapses
    anyOf[T, null] to T, keeping every description byte-for-byte. Doing it in
    one place also means a future SDK that stops accepting anyOf needs one fix.
    """
    props: dict[str, Any] = {}
    for key, spec in (schema.get("properties") or {}).items():
        if "anyOf" in spec:
            non_null = [a for a in spec["anyOf"] if a.get("type") != "null"]
            base = dict(non_null[0]) if non_null else {"type": "string"}
        else:
            base = {"type": spec.get("type", "string")}
        clean: dict[str, Any] = {"type": base.get("type", "string")}
        if spec.get("description"):
            clean["description"] = spec["description"]
        if spec.get("enum"):
            clean["enum"] = spec["enum"]
        props[key] = clean
    return {
        "type": "object",
        "properties": props,
        "required": list(schema.get("required") or []),
    }


class McpRegistry:
    def __init__(self, clients: dict[str, McpClient],
                 local_search: Callable[[str, int], list[dict[str, Any]]],
                 unconfigured: list[str] | None = None) -> None:
        self.clients = clients
        self.local_search = local_search
        # Servers that were configured (named in MCP_SERVERS) but had no API
        # key. They are not in `clients` — there is nothing to call — but
        # they must still be reportable, or an unset env var looks exactly
        # like a healthy system with nothing to say.
        self.unconfigured = list(unconfigured or [])

    def degraded(self) -> list[str]:
        unhealthy = (n for n, c in self.clients.items() if not c.healthy)
        return sorted(set(unhealthy) | set(self.unconfigured))

    def declarations(self) -> list[dict[str, Any]]:
        decls: list[dict[str, Any]] = [{
            "name": LOCAL_TOOL,
            "description": (
                "Işık'ın kendi okul verisinde arama yapar: ödevler, sınavlar, "
                "notlar, ders programı, duyurular, ders içerikleri. Işık'a özel "
                "her soru için BU aracı kullan — konu/müfredat bilgisi için değil."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {
                    "type": "string",
                    "description": "Aranacak ifade (ör. 'matematik ödevi', 'sınav tarihleri')."}},
                "required": ["query"],
            },
        }]
        for local_name, (server, mcp_name) in TOOL_ALLOWLIST.items():
            client = self.clients.get(server)
            if client is None:
                continue
            spec = next((t for t in client.list_tools()
                         if t.get("name") == mcp_name), None)
            if spec is None:
                logger.warning("MCP %s does not expose %s", server, mcp_name)
                continue
            decls.append({
                "name": local_name,
                "description": spec.get("description", ""),
                "parameters": sanitize_schema(spec.get("inputSchema") or {}),
            })
        return decls

    def dispatch(self, name: str, args: dict[str, Any]) -> ToolOutcome:
        if name == LOCAL_TOOL:
            return self._dispatch_local(args)
        if name not in TOOL_ALLOWLIST:
            return ToolOutcome(ok=False, error=f"bilinmeyen araç: {name}")

        server, mcp_name = TOOL_ALLOWLIST[name]
        client = self.clients.get(server)
        if client is None:
            return ToolOutcome(ok=False, error=f"sunucu yapılandırılmadı: {server}")

        result: McpToolResult = client.call_tool(mcp_name, args)
        if not result.ok:
            return ToolOutcome(ok=False, error=result.error or "araç hatası")

        kind = _KIND_BY_TOOL.get(name, "mufredat")
        return ToolOutcome(
            ok=True,
            text=result.text,
            citations=[{
                "kind": kind,
                "label": self._label(kind, name, args),
                "locator": {"tool": name, "args": args, "server": server},
                "snippet": result.text[:400],
                "confidence": 0.9,
            }],
        )

    def _dispatch_local(self, args: dict[str, Any]) -> ToolOutcome:
        query = str(args.get("query", "")).strip()
        try:
            rows = self.local_search(query, 8)
        except Exception as exc:
            # local_search is caller-supplied and, unlike the MCP path,
            # carries no contract against raising. A failure here must not
            # take the whole dispatch() call down with it — and must not be
            # swallowed either, per "sessiz arıza yok".
            logger.error("local_search failed for %r: %s", query, exc)
            return ToolOutcome(ok=False, error=f"yerel arama hatası: {exc}")

        rows = [r for r in rows if isinstance(r, dict)]
        citations = []
        for r in rows:
            try:
                confidence = float(r.get("confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            citations.append({
                "kind": "ogrenci",
                "label": os.path.basename(str(r.get("path", ""))) or "okul verisi",
                "locator": {"path": r.get("path", ""),
                            "chunk_index": r.get("chunk_index", 0)},
                "snippet": str(r.get("snippet", ""))[:400],
                "confidence": confidence,
            })
        text = "\n\n".join(str(r.get("snippet", "")) for r in rows) or "(kayıt yok)"
        return ToolOutcome(ok=True, text=text, citations=citations)

    @staticmethod
    def _label(kind: str, tool: str, args: dict[str, Any]) -> str:
        if kind == "kitap":
            doc = args.get("document_id")
            page = args.get("page") or args.get("page_range")
            if doc and page:
                return f"Ders kitabı #{doc} · s.{page}"
            return "Ders kitabı"
        if kind == "oer":
            return "Açık eğitsel kaynak"
        subject = args.get("subject") or args.get("q") or ""
        return f"MEB müfredatı · {subject}" if subject else "MEB müfredatı"


def build_registry(local_search: Callable[[str, int], list[dict[str, Any]]]
                   ) -> McpRegistry:
    """Wire the configured servers. A server with no key is simply absent —
    its tools are not declared — but it is still named by degraded(), so an
    unset env var never looks like a healthy system with nothing to say."""
    clients: dict[str, McpClient] = {}
    unconfigured: list[str] = []
    for name, (url, env_key) in MCP_SERVERS.items():
        key = os.environ.get(env_key, "").strip()
        if not key:
            logger.warning("MCP %s disabled: %s not set", name, env_key)
            unconfigured.append(name)
            continue
        clients[name] = McpClient(name=name, url=url, api_key=key)
    return McpRegistry(clients=clients, local_search=local_search,
                       unconfigured=unconfigured)
