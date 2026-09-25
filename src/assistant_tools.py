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
from datetime import datetime
from typing import Any, Callable

from src.mcp_client import McpClient, McpToolResult
from src import assistant_modules

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

# Curriculum tools that take a `grade` filter. A search the model did not
# scope is scoped to Işık's own grade (`McpRegistry.sinif`): measured
# 2026-09-25, an unscoped outcome search mixed every year's results.
SINIF_ARACLARI = frozenset({"kazanim_ara", "kazanim_listele", "mufredat_ara",
                            "kitap_listele", "figur_ara"})

# Every pdf_url/source_url in the maarif corpus answers HTTP 500 since MEB
# moved its files in summer 2026 (CureoHub mcp-servers/mufredat-mcp/
# DISCOVERY-UPSTREAM-2026-09.md §2). They are removed before the model reads a
# result, so it cannot hand the reader a dead link.
OLU_BAGLANTILAR = frozenset({"pdf_url", "source_url"})


def _json_parcalari(text: str) -> list[Any] | None:
    """The maarif server answers with one or more JSON values back to back
    (one content block per list item). None when the text is not that."""
    decoder = json.JSONDecoder()
    out: list[Any] = []
    i = 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        try:
            value, i = decoder.raw_decode(text, i)
        except ValueError:
            return None
        out.append(value)
    return out or None


def _baglantisiz(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _baglantisiz(v) for k, v in value.items() if k not in OLU_BAGLANTILAR}
    if isinstance(value, list):
        return [_baglantisiz(v) for v in value]
    return value


LOCAL_TOOL = "ogrenci_verisi_ara"
# The homework list as Bugün and İşler show it (portal rows, photo-added ones,
# Işık's own "Yaptım" marks). Declared only when the caller supplies a source.
ODEV_TOOL = "odev_listesi"
ODEV_ATIF = "Ödevlerim · güncel liste"

_GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_COZULMUS = {"yaptı", "yapti", "yapmadı", "yapmadi", "eksik", "tamamlandı", "tamamlandi"}
_GECMIS_GUN = 14
_BOLUM_SINIRI = 10


def bugun_satiri(simdi: datetime) -> str:
    """"Bugün: Perşembe 24.09.2026 16:10" — the model has no clock of its own."""
    return f"Bugün: {_GUNLER[simdi.weekday()]} {simdi:%d.%m.%Y %H:%M}"


def _teslim(deger: str) -> datetime | None:
    s = str(deger or "").strip()
    for bicim in ("%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, bicim)
        except ValueError:
            continue
    return None


def _goreli(teslim: datetime, simdi: datetime) -> str:
    fark = (teslim.date() - simdi.date()).days
    if fark == 0:
        return "bugün"
    if fark == 1:
        return "yarın"
    if fark == -1:
        return "dün"
    return f"{fark} gün sonra" if fark > 0 else f"{-fark} gün önce"


def odev_listesi_metni(rows: list[dict[str, Any]], simdi: datetime) -> str:
    """The homework list for the model, in the groups İşler uses.

    Written for a reader, not a parser: the model quotes from it. Work Işık
    marked "Yaptım" is never listed as still to do — that is the mistake the
    smoke test caught — and the open work carries the teacher's instructions."""
    bas = bugun_satiri(simdi)
    if not rows:
        return f"{bas}\nŞu an portalda kayıtlı ödev yok."

    yapilacak, yaptim, gecmis, cozulmus = [], [], [], []
    eski = 0
    for r in rows:
        teslim = _teslim(r.get("Ödev Son Teslim Tarihi", ""))
        # A deadline more than two weeks past is history, whatever its status:
        # on 2026-09-24 twelve "Yaptım" rows from March sorted ahead of this
        # week's and pushed it past the cap. They are counted, not hidden.
        if teslim is not None and (simdi - teslim).days > _GECMIS_GUN:
            eski += 1
            continue
        cozuldu = r.get("teacher_resolved")
        if cozuldu is None:
            cozuldu = str(r.get("Ödev Durumu", "")).strip().lower() in _COZULMUS
        if cozuldu:
            cozulmus.append((teslim, r))
        elif r.get("student_marked_done"):
            yaptim.append((teslim, r))
        elif teslim is not None and teslim < simdi:
            gecmis.append((teslim, r))
        else:
            yapilacak.append((teslim, r))

    def satir(teslim: datetime | None, r: dict[str, Any], aciklama: bool = False) -> str:
        ad = " — ".join(x for x in (str(r.get("normalized_course") or r.get("Ders Adı") or "").strip(),
                                    str(r.get("Ödev Başlığı") or "").strip()) if x)
        zaman = (f"teslim {_GUNLER[teslim.weekday()]} {teslim:%d.%m.%Y %H:%M} ({_goreli(teslim, simdi)})"
                 if teslim else "teslim tarihi okunamadı")
        metin = f"- {ad} · {zaman}"
        if aciklama:
            detay = " ".join(str((r.get("detail") or {}).get("description") or "").split())
            if detay:
                kisa = detay if len(detay) <= 240 else detay[:240].rsplit(" ", 1)[0] + " …"
                metin += f"\n  Açıklama: {kisa}"
        return metin

    def sirala(grup):
        return sorted(grup, key=lambda x: (x[0] is None, x[0] or simdi))

    parcalar = [bas + " (portal listesi, Işık'ın \"Yaptım\" işaretleriyle)"]
    parcalar.append(f"YAPILACAK ({len(yapilacak)}):\n" + ("\n".join(
        satir(t, r, aciklama=True) for t, r in sirala(yapilacak)[:_BOLUM_SINIRI]) or "- yok"))
    if yaptim:
        parcalar.append(f"YAPTIM DEDİ, ÖĞRETMEN HENÜZ DEĞERLENDİRMEDİ ({len(yaptim)}):\n"
                        + "\n".join(satir(t, r) for t, r in sirala(yaptim)[:_BOLUM_SINIRI]))
    if gecmis:
        parcalar.append(f"SÜRESİ GEÇTİ, YAPTIM İŞARETİ YOK — son {_GECMIS_GUN} gün ({len(gecmis)}):\n"
                        + "\n".join(satir(t, r) for t, r in sirala(gecmis)[:_BOLUM_SINIRI]))
    if cozulmus:
        dagilim: dict[str, int] = {}
        for _, r in cozulmus:
            d = str(r.get("Ödev Durumu", "")).strip() or "?"
            dagilim[d] = dagilim.get(d, 0) + 1
        parcalar.append(f"ÖĞRETMEN DEĞERLENDİRDİ — son {_GECMIS_GUN} gün: {len(cozulmus)} ödev ("
                        + ", ".join(f"{k} {v}" for k, v in sorted(dagilim.items())) + ")")
    if eski:
        parcalar.append(f"Not (okura aktarma): teslimi {_GECMIS_GUN} günden eski {eski} ödev "
                        "bu listede yok. Yalnız eski ödevler sorulursa `ogrenci_verisi_ara` "
                        "ile bak.")
    return "\n\n".join(parcalar)

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

    Becomes the tool's `input_schema` on the Messages API (Claude, since
    2026-09-24). A sanitiser rather than a rewriter: it drops `title` noise and
    collapses anyOf[T, null] to T, keeping every description byte-for-byte and
    the element type of every array. Doing it in one place means a model that
    stops accepting some construct needs one fix.
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
        if clean["type"] == "array":
            # An array without `items` is what took the assistant down: from
            # 2026-09-22 every model answered 400 INVALID_ARGUMENT
            # "…[include_fragments].items: missing field", because this kept
            # only type/description/enum and dropped the element type.
            items = base.get("items") or spec.get("items") or {}
            item = {"type": items.get("type", "string")} if isinstance(items, dict) else {"type": "string"}
            if isinstance(items, dict) and items.get("enum"):
                item["enum"] = items["enum"]
            clean["items"] = item
        props[key] = clean
    return {
        "type": "object",
        "properties": props,
        "required": list(schema.get("required") or []),
    }


# ogrenci_verisi_ara's tool body (task-1 brief §5): the model gets the full
# chunk text, not the 260-char citation snippet — capped per hit so one huge
# chunk cannot crowd out the rest, and in total so the whole body fits inside
# chat_with_tools' 4,000-char per-result truncation (assistant_core.py
# ChatClient.chat_with_tools slices tool_result content to [:4000]).
_YEREL_ISABET_SINIRI = 1200
_YEREL_TOPLAM_SINIRI = 3900


def _kirp(metin: str, sinir: int) -> str:
    if len(metin) <= sinir:
        return metin
    if sinir <= 2:
        return metin[:sinir]
    govde = sinir - 2  # reserve room for the " …" suffix itself
    kesik = metin[:govde].rsplit(" ", 1)[0]
    return (kesik or metin[:govde]) + " …"


def _yerel_tam_metin(rows: list[dict[str, Any]]) -> str:
    """Each hit's full chunk text (not the snippet), joined; per-hit and
    total budgets both enforced so the model reads more than a 260-char
    fragment without the body blowing past chat_with_tools' cutoff."""
    parcalar: list[str] = []
    toplam = 0
    for r in rows:
        parca = str(r.get("text") or r.get("snippet") or "").strip()
        if not parca:
            continue
        parca = _kirp(parca, _YEREL_ISABET_SINIRI)
        ayrac = 2 if parcalar else 0  # "\n\n" between hits
        if toplam + ayrac + len(parca) > _YEREL_TOPLAM_SINIRI:
            kalan = _YEREL_TOPLAM_SINIRI - toplam - ayrac
            if kalan > 0:
                parcalar.append(_kirp(parca, kalan))
            break
        parcalar.append(parca)
        toplam += ayrac + len(parca)
    return "\n\n".join(parcalar) or "(kayıt yok)"


# content/eba and content/sebitv filenames carry the grade as a bare digit
# token, e.g. "Matematik 6 1. Kitap.pdf" (6 = grade, "1." = volume number —
# the trailing period on "1." is what tells the two apart: isdigit() is
# False for "1."). Unmatched filenames keep their plain basename label.
_SINIF_ETIKETLI_DIZINLER = ("content/eba/", "content/sebitv/")


def _sinif_etiketi_dosyadan(dosya_adi: str) -> str | None:
    kok = os.path.splitext(dosya_adi)[0]
    for token in kok.split():
        if token.isdigit():
            n = int(token)
            if 1 <= n <= 12:
                return f"{n}. sınıf"
    return None


def _yerel_isabet_etiketi(path: str) -> str:
    base = os.path.basename(path) or "okul verisi"
    if path.startswith(_SINIF_ETIKETLI_DIZINLER):
        sinif = _sinif_etiketi_dosyadan(base)
        if sinif:
            baslik = os.path.splitext(base)[0]
            return f"{sinif} · {baslik}"
    return base


class McpRegistry:
    def __init__(self, clients: dict[str, McpClient],
                 local_search: Callable[[str, int], list[dict[str, Any]]],
                 unconfigured: list[str] | None = None,
                 module_index: Any = None,
                 odev_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                 sinif: Callable[[], str | None] | None = None) -> None:
        self.clients = clients
        # Işık's grade in the corpus's form ("7.Sınıf"), read when asked so a
        # new school year needs no restart. None, or a None answer, means
        # unknown: no grade is then invented.
        self.sinif = sinif
        self.local_search = local_search
        # Servers that were configured (named in MCP_SERVERS) but had no API
        # key. They are not in `clients` — there is nothing to call — but
        # they must still be reportable, or an unset env var looks exactly
        # like a healthy system with nothing to say.
        self.unconfigured = list(unconfigured or [])
        # Published edupedia modules (src/assistant_modules.py). Local and read-only; None keeps
        # the registry usable in tests and tools that have no catalog.
        self.module_index = module_index
        # The rows /api/homework serves (src/dashboard_api._canli_odevler).
        # None in tests and tools with no dashboard: the tool is not declared.
        self.odev_kaynagi = odev_kaynagi

    def degraded(self) -> list[str]:
        unhealthy = {n for n, c in self.clients.items() if not c.healthy}
        modules = set(self.module_index.degraded()) if self.module_index is not None else set()
        return sorted(unhealthy | set(self.unconfigured) | modules)

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
        if self.odev_kaynagi is not None:
            decls.append({
                "name": ODEV_TOOL,
                "description": (
                    "Işık'ın ödev listesi, Bugün ve İşler sayfalarının gösterdiği haliyle: "
                    "yapılacaklar (teslim zamanı ve öğretmenin talimatıyla), Işık'ın 'Yaptım' "
                    "dedikleri, süresi geçenler. Ödev sorularında (ne var, ne zaman teslim, "
                    "neyi yaptı) önce BU aracı kullan — ödevin durumu için tek güvenilir kaynak."
                ),
                "parameters": {"type": "object", "properties": {}},
            })
        if self.module_index is not None:
            decls.append(dict(assistant_modules.DECLARATION))
        for local_name, (server, mcp_name) in TOOL_ALLOWLIST.items():
            client = self.clients.get(server)
            if client is None:
                continue
            spec = next((t for t in client.list_tools()
                         if t.get("name") == mcp_name), None)
            if spec is None:
                logger.warning("MCP %s does not expose %s", server, mcp_name)
                continue
            description = spec.get("description", "")
            sinif = self._sinif()
            if sinif and local_name in SINIF_ARACLARI:
                description += (f"\n\nIşık {sinif} öğrencisi: `grade` vermezsen "
                                f"'{sinif}' kullanılır. Önceki yılın konusu için sınıfı açıkça ver.")
            decls.append({
                "name": local_name,
                "description": description,
                "parameters": sanitize_schema(spec.get("inputSchema") or {}),
            })
        return decls

    def _sinif(self) -> str | None:
        try:
            return (self.sinif() or None) if self.sinif is not None else None
        except Exception:  # noqa: BLE001 — an unknown grade is a normal state
            return None

    def dispatch(self, name: str, args: dict[str, Any], ilerleme_izni: bool = False) -> ToolOutcome:
        if name == LOCAL_TOOL:
            return self._dispatch_local(args)
        if name == ODEV_TOOL and self.odev_kaynagi is not None:
            return self._dispatch_odev()
        if name == assistant_modules.TOOL_NAME:
            return self._dispatch_modules(args, ilerleme_izni is True)
        if name not in TOOL_ALLOWLIST:
            return ToolOutcome(ok=False, error=f"bilinmeyen araç: {name}")
        if assistant_modules.contains_progress(args):
            # Spec §6.4: module progress never leaves TED. This catches keys copied verbatim from
            # modul_ara's output; a paraphrase is not caught (plan K-S6, accepted residual risk).
            return ToolOutcome(ok=False, error=(
                "ilerleme verisi yan filo sunucularına gönderilmez; bu alanları argümandan çıkar"))

        server, mcp_name = TOOL_ALLOWLIST[name]
        client = self.clients.get(server)
        if client is None:
            return ToolOutcome(ok=False, error=f"sunucu yapılandırılmadı: {server}")

        sinif = self._sinif()
        if sinif and name in SINIF_ARACLARI and not args.get("grade"):
            args = {**args, "grade": sinif}

        result: McpToolResult = client.call_tool(mcp_name, args)
        if not result.ok:
            return ToolOutcome(ok=False, error=result.error or "araç hatası")

        text = result.text
        parcalar = _json_parcalari(text) if server == "maarif-mufredat" else None
        if parcalar is not None:
            text = "\n".join(json.dumps(_baglantisiz(p), ensure_ascii=False, indent=2)
                             for p in parcalar)

        kind = _KIND_BY_TOOL.get(name, "mufredat")
        return ToolOutcome(
            ok=True,
            text=text,
            citations=[{
                "kind": kind,
                "label": self._label(kind, name, args, parcalar),
                "locator": {"tool": name, "args": args, "server": server},
                "snippet": text[:400],
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
                "label": _yerel_isabet_etiketi(str(r.get("path", ""))),
                "locator": {"path": r.get("path", ""),
                            "chunk_index": r.get("chunk_index", 0)},
                # The citation panel keeps the short snippet (≤260 chars, set
                # by the retriever) — only the model's own tool body gets the
                # full chunk text below.
                "snippet": str(r.get("snippet", ""))[:400],
                "confidence": confidence,
            })
        text = _yerel_tam_metin(rows)
        return ToolOutcome(ok=True, text=text, citations=citations)

    def _dispatch_odev(self) -> ToolOutcome:
        try:
            rows = self.odev_kaynagi() or []
        except Exception as exc:  # noqa: BLE001 — told to the model, never raised through the loop
            logger.error("odev_listesi failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"ödev listesi okunamadı: {type(exc).__name__}")
        metin = odev_listesi_metni(rows, datetime.now())
        return ToolOutcome(ok=True, text=metin, citations=[{
            "kind": "ogrenci",
            "label": ODEV_ATIF,
            "locator": {"tool": ODEV_TOOL},
            "snippet": metin[:400],
            "confidence": 1.0,
        }])

    def _dispatch_modules(self, args: dict[str, Any], ilerleme_izni: bool) -> ToolOutcome:
        if self.module_index is None:
            return ToolOutcome(ok=False, error="modül kataloğu bağlanmadı")
        try:
            text, citations = self.module_index.ara(
                sorgu=args.get("sorgu", ""), ders=args.get("ders"), sinif=args.get("sinif"),
                ilerleme_izni=ilerleme_izni)
        except Exception as exc:  # noqa: BLE001 — reported to the model, never raised through the loop
            logger.error("modul_ara failed: %s", type(exc).__name__)
            return ToolOutcome(ok=False, error=f"modül araması hatası: {type(exc).__name__}")
        return ToolOutcome(ok=True, text=text, citations=citations)

    @staticmethod
    def _label(kind: str, tool: str, args: dict[str, Any],
               parcalar: list[Any] | None = None) -> str:
        if kind == "kitap":
            doc = args.get("document_id")
            page = args.get("page") or args.get("page_range")
            # The book's name, not its corpus number: "Ders kitabı #213" told
            # the reader nothing.
            belge = parcalar[0].get("document") if parcalar and isinstance(parcalar[0], dict) else None
            baslik = belge.get("title") if isinstance(belge, dict) else None
            if baslik and page:
                return f"{baslik} · s.{page}"
            if doc and page:
                return f"Ders kitabı #{doc} · s.{page}"
            return "Ders kitabı"
        if kind == "oer":
            return "Açık eğitsel kaynak"
        subject = args.get("subject") or args.get("q") or ""
        return f"MEB müfredatı · {subject}" if subject else "MEB müfredatı"


def build_registry(local_search: Callable[[str, int], list[dict[str, Any]]],
                   module_index: Any = None,
                   odev_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                   sinif: Callable[[], str | None] | None = None) -> McpRegistry:
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
                       unconfigured=unconfigured, module_index=module_index,
                       odev_kaynagi=odev_kaynagi, sinif=sinif)
