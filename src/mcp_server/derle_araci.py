"""edupedia_derle and edupedia_onizle: run-anchored compile into immutable drafts (spec §5.1; plan K-P8)."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from src import module_store as ms
from src.mcp_server import alt_metin, derleme, gates
from src.mcp_server.derleme import DerlemeHatasi, GomuluVarlik
from src.mcp_server.runs import RUN_ID_RE, RunStore
from src.mcp_server.taslak import DraftStore

logger = logging.getLogger(__name__)

DETAIL_MAX = 300
NEXT_OK = "Önizleme için edupedia_onizle(taslak_id); yayın için edupedia_yayinla(taslak_id, ted_link?)."
NEXT_FAIL = "FAIL veren kapıları MODULE_DATA'da düzelt ve edupedia_derle'yi tekrar çağır; HTML'i kendin yazma."
ALT_DAYANAK_NOTU = ("Alt metindeki özel ad ve sayılar kitabın kendi metninde geçmeli: figür altı yazısı "
                    "(edupedia_gorsel kaynak_verisi.varlik.kitap_altyazisi), etiket ya da çerçeve sayfaları. Yalnız "
                    "betim'de (yapay zekâ ya da sağlayıcı betimi) geçmek yetmez. Kitaptaki gibi yaz; bilerek farklı "
                    "yazdıysan nedenini meta.assets[i].alt_gerekce'ye yaz (en az 20 karakter), derleme o zaman "
                    "uyarıyla geçer.")
AssetLoader = Callable[[str], Mapping[str, GomuluVarlik]]


def _run_mismatch(run: dict[str, Any], data: dict[str, Any]) -> dict[str, Any] | None:
    cerceve = run.get("cerceve") or {}
    frame = (data.get("verification") or {}).get("frame_source") or {}
    if cerceve.get("kind") == "textbook" and cerceve.get("document_id") is not None:
        if frame.get("document_id") != cerceve["document_id"]:
            return {"status": "cerceve_uyusmazligi",
                    "run_cercevesi": {"kind": "textbook", "document_id": cerceve["document_id"]},
                    "module_cercevesi": {"kind": frame.get("kind"), "document_id": frame.get("document_id")}}
    run_codes = {k.get("code") for k in run.get("kazanimlar") or [] if isinstance(k, dict) and k.get("code")}
    codes = [o.get("code") for o in (data.get("curriculum") or {}).get("outcomes") or [] if isinstance(o, dict)]
    outside = sorted({c for c in codes if c and c not in run_codes})
    if outside:
        return {"status": "kazanim_run_disi", "kodlar": outside, "run_kazanimlari": sorted(run_codes)}
    return None


class Derleyici:
    def __init__(self, runs: RunStore, drafts: DraftStore, parent_origin: str, dashboard_public_url: str,
                 assets: AssetLoader | None = None, clock: Callable[[], float] = time.time) -> None:
        self.runs = runs
        self.drafts = drafts
        self.parent_origin = parent_origin
        self.dashboard_public_url = dashboard_public_url.rstrip("/")
        self.assets = assets
        self.clock = clock

    def derle(self, email: str, run_id: str, module_data: Any) -> dict[str, Any]:
        base: dict[str, Any] = {"run_id": run_id, "mcp_verified": False}
        run = self.runs.load(run_id) if RUN_ID_RE.match(run_id or "") else None
        if run is None:
            return {**base, "status": "run_bulunamadi",
                    "not": "Önce edupedia_kapsam çağır; derleme müfredat dayanağı kayıtlı bir run_id ister."}
        if isinstance(module_data, str):
            try:
                module_data = json.loads(module_data)
            except ValueError:
                return {**base, "status": "sema_hatasi", "hatalar": ["module_data geçerli JSON değil"]}
        try:
            try:
                size = derleme.girdi_boyutu(module_data)
                if size > derleme.MAX_INPUT_BYTES:
                    raise DerlemeHatasi("cok_buyuk", bayt=size, sinir=derleme.MAX_INPUT_BYTES)
                # Varlık kayıtları önce okunur: raster görselin alt/baslik zorunluluğu şema hatalarıyla tek
                # listede döner (yazar iki turda düzeltmez).
                varliklar = self.assets(run_id) if self.assets else {}
                errors = derleme.girdi_hatalari(module_data, varliklar)
                if errors:
                    raise DerlemeHatasi("sema_hatasi", hatalar=errors)
                mismatch = _run_mismatch(run, module_data)
                if mismatch:
                    return {**base, **mismatch}
                # Kanun M3.6 (KB-10): alt metnin adları ve sayıları figürün açıklamasında ya da çerçeve
                # sayfalarında geçer; gerekçesiz dayanaksız ad derlemeyi durdurur, gerekçeli olan uyarıdır.
                sayfa_metni = "\n".join(p["text"] for p in self.runs.pages(run_id))
                dayanaksiz, uyarilar = alt_metin.alt_metin_dayanagi(module_data, varliklar, sayfa_metni)
                if dayanaksiz:
                    return {**base, "status": "alt_metin_dayanaksiz", "hatalar": dayanaksiz, "not": ALT_DAYANAK_NOTU}
                html = derleme.derle(module_data, varliklar, self.parent_origin)
            except DerlemeHatasi as exc:
                return {**base, "status": exc.status, **exc.detay}
            # Second, outer boundary (review 1a/1b): derleme.derle() above can also raise a bare
            # ValueError/RuntimeError from sablon.engine_template() for a malformed parent_origin
            # or a drifted vendored template — neither is a DerlemeHatasi, so the inner except
            # above never sees it. gates.run_gates() and drafts.save() have no per-call guard of
            # their own either. Anything that reaches here is closed to a non-leaking status
            # instead of an uncaught exception reaching MCPServer's generic error handler (which
            # would return the raw Python exception text as the tool's error message).
            report = gates.run_gates(html)
            summary = derleme.kapi_ozeti(report)
            meta = module_data["meta"]
            taslak_id = self.drafts.new_id()
            record = self.drafts.save(taslak_id, html, {
                "run_id": run_id, "created_by": email,
                "created_at": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="seconds"),
                "meta": {key: meta.get(key) for key in ("id", "title", "subject", "gradeLevel", "mode")},
                "sure_dk": meta.get("estimatedMinutes") if isinstance(meta.get("estimatedMinutes"), int)
                and not isinstance(meta.get("estimatedMinutes"), bool) and 0 < meta["estimatedMinutes"] <= 240 else None,
                "ted_link": meta.get("tedLink"),
                "outcomes": [o.get("code") for o in module_data["curriculum"].get("outcomes") or [] if isinstance(o, dict)],
                "frame_source": module_data["verification"].get("frame_source"),
                "dogrulama": derleme.dogrulama_ozeti(module_data),
                "kazanim_ayrintilari": derleme.kazanim_ozeti(module_data),
                "coverage": run.get("coverage") or {},
                "assets": [ref["asset_id"] for ref in meta.get("assets") or []],
                "gates": summary, "kapilar": report, "parent_origin": self.parent_origin,
                **({"uyarilar": uyarilar} if uyarilar else {}),
            })
        except Exception:
            logger.exception("edupedia_derle iç hatası (run_id=%s)", run_id)
            return {**base, "status": "sunucu_hatasi",
                    "not": "Derleme sunucu tarafında tamamlanamadı; yöneticiye bildir. "
                           "MODULE_DATA'yı değiştirmek bu hatayı çözmez."}
        kapilar = {}
        for gate, row in report.items():
            entry = {"status": row["status"]}
            if row["status"] in ("FAIL", "WARN") and row.get("detail"):
                entry["detay"] = row["detail"][:DETAIL_MAX]
            kapilar[gate] = entry
        return {**base, "status": "ok", "taslak_id": taslak_id, "kapi_ozeti": summary, "kapilar": kapilar,
                **({"uyarilar": uyarilar} if uyarilar else {}),
                "bayt": record["bayt"], "sonraki_adim": NEXT_FAIL if summary["fail"] else NEXT_OK}

    def onizle(self, email: str, taslak_id: str) -> dict[str, Any]:
        record = self.drafts.load(taslak_id) if ms.valid_taslak_id(taslak_id) else None
        if record is None:
            return {"status": "taslak_bulunamadi", "taslak_id": taslak_id, "mcp_verified": False}
        return {"status": "ok", "taslak_id": taslak_id,
                "url": f"{self.dashboard_public_url}/moduller/taslak/{taslak_id}",
                "kapi_ozeti": record.get("gates"),
                "not": "Bağlantı TEDY aile girişi ister; modül 10 dakikalık biletle açılır.",
                "mcp_verified": False}
