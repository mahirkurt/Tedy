"""Business logic for ted-mcp tools, kept free of FastMCP so it is unit-testable."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from src import roles
from src.mcp_server import __version__, gates, rehber, vendor_sync
from src.mcp_server.config import Settings
from src.mcp_server.coverage import Coverage
from src.mcp_server.dashboard_context import DashboardContext, DashboardUnavailable
from src.mcp_server.federation import ANAMNESIS, EGITIM_KAYNAK, MUFREDAT, Federation, FederationError
from src.mcp_server.kapsam import KapsamBuilder
from src.mcp_server.kaynak_oku import KaynakOkuyucu, wrap_kaynak_verisi
from src.mcp_server.runs import RunStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Lightweight health call per fleet server for edupedia_durum(canli=True).
_HEALTH_CALLS: dict[str, tuple[str, dict[str, Any]]] = {
    MUFREDAT: ("server_info", {}),
    EGITIM_KAYNAK: ("kb_server_info", {}),
    ANAMNESIS: ("corpus_stats", {"collection": "edupedia:run:000000000000"}),
}


def app_revision(root: Path = PROJECT_ROOT) -> str | None:
    """Deploy revision from a REVISION file next to the project root; None when absent."""
    try:
        text = (root / "REVISION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


class Tools:
    def __init__(self, settings: Settings, federation: Federation, clock: Callable[[], float] = time.time,
                 dashboard: DashboardContext | None = None, runs: RunStore | None = None) -> None:
        self.settings = settings
        self.federation = federation
        self.clock = clock
        self.dashboard = dashboard
        self.runs = runs if runs is not None else RunStore(settings.data_dir)

    def durum(self, email: str, canli: bool = False) -> dict[str, Any]:
        provenance = vendor_sync.load_provenance()
        filo = {
            name: ("yapılandırılmış" if self.federation.configured(name) else "anahtar yok")
            for name in self.settings.servers
        }
        body: dict[str, Any] = {
            "status": "ok",
            "surum": __version__,
            "app_revision": app_revision(),
            "kullanici": {"email": email, "rol": roles.role_of(email)},
            "kapi_sayisi": gates.gate_count(),
            "vendor": {"kaynak_commit": provenance.get("source_commit"), "esitlendi": provenance.get("synced_at")},
            "filo": filo,
            "dashboard_anahtari": bool(self.settings.dashboard_api_key),
            "medya_butcesi": None,
            "notlar": [
                "Medya bütçesi, derleme ve yayın araçları sonraki alt projede gelir.",
                "Boş sonuç yokluk kanıtı değildir; her getirim aracı kapsam manifestosu döner.",
            ],
            "mcp_verified": False,
        }
        if canli:
            cov = Coverage()
            for name in self.settings.servers:
                if not self.federation.configured(name):
                    cov.skipped(name, "anahtar yok")
                    continue
                tool, args = _HEALTH_CALLS[name]
                try:
                    self.federation.call(name, tool, args, beklenen="nesne")
                    cov.hit(name)
                except FederationError as exc:
                    cov.degraded(name, exc.reason)
            body["coverage"] = cov.as_dict()
        return body

    def rehber(self, bolum: str | None = None, parca: int = 1, ara: str | None = None) -> dict[str, Any]:
        if ara:
            return rehber.search(ara)
        return rehber.guide(bolum or "akis", parca=parca)

    def baglam(self, email: str, gun: int = 7) -> dict[str, Any]:
        gun = max(1, min(int(gun), 60))
        base: dict[str, Any] = {
            "gun": gun,
            "caveat": "Veriler okul portalından 15 dakikada bir çekilir; yeni duyurulan sınav veya ödev eksik olabilir.",
            "mcp_verified": False,
        }
        if self.dashboard is None or not self.settings.dashboard_api_key:
            cov = Coverage()
            cov.skipped("tedy-dashboard", "anahtar yok")
            return {**base, "status": "degraded", "coverage": cov.as_dict()}
        cov = Coverage()
        try:
            data = self.dashboard.upcoming(gun)
        except DashboardUnavailable as exc:
            cov.degraded("tedy-dashboard", exc.reason)
            return {**base, "status": "degraded", "coverage": cov.as_dict()}
        if data["sinavlar"] or data["odevler"]:
            cov.hit("tedy-dashboard")
        else:
            cov.empty("tedy-dashboard")
        return {**base, "status": "ok", **data, "coverage": cov.as_dict()}

    def kapsam(self, email: str, ders: str, sinif: str, konu: str | None = None,
               kazanim_kodu: str | None = None) -> dict[str, Any]:
        return KapsamBuilder(self.federation, self.runs, self.clock).build(email, ders, sinif, konu, kazanim_kodu)

    def kaynak_oku(self, email: str, run_id: str, soru: str, top_k: int = 5) -> dict[str, Any]:
        body = KaynakOkuyucu(self.federation, self.runs).oku(run_id, soru, top_k=top_k)
        return wrap_kaynak_verisi(body)
