"""edupedia_medya (spec §8; plan K-P12, K-P13, K-P22).

Narration is automatic only when its price is verified and the run stays under 3,000 characters;
music and video always need the approval token the estimate step returns. Async jobs (video,
comfyui) are started once, recorded in the ledger with their job id and polled with is_kimligi.
Provider free text is never echoed. Voice cloning and voice design are not reachable from here.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable

from src.mcp_server.butce import (BELIRSIZ_NEDENLER, ONAY_TTL_SECONDS, TAHMIN_NOTU, Butce, ButceAsildi,
                                  OnayKullanildi)
from src.mcp_server.coverage import Coverage
from src.mcp_server.federation import COMFYUI, MINIMAX, TOOL_BUDGET_SECONDS, Federation, FederationError
from src.mcp_server.runs import RUN_ID_RE, RunStore
from src.mcp_server.varliklar import AssetStore, GuvenliIndirici, VarlikHatasi

TURLER = ("ses", "muzik", "video")
SES_MODUL_SINIRI = 3000
ISTEK_MAX = {"ses": 3000, "muzik": 900, "video": 1000}
CREDITS = {
    "minimax.ses": "Seslendirme: yapay zekâ ile üretildi (MiniMax speech-2.8-hd)",
    "minimax.muzik": "Müzik: yapay zekâ ile üretildi (MiniMax music-2.6)",
    "minimax.video": "Video: yapay zekâ ile üretildi (MiniMax Hailuo)",
    "comfyui.muzik": "Müzik: yapay zekâ ile üretildi (ComfyUI)",
    "comfyui.video": "Video: yapay zekâ ile üretildi (ComfyUI Wan)",
}
SLOT = {"ses": "<teachSegmentId>.audio", "muzik": "<teachSegmentId>.audio", "video": "<teachSegmentId>.visual"}
ONAY_NOTU = ("Tahmini tutarı kullanıcıya göster ve açık onay al; sonra aynı tür ve istekle onay_belirteci "
             "vererek tekrar çağır. " + TAHMIN_NOTU)

# T14-3: async jobs (video, comfyui) are started once and remembered by job id; only a job id
# fullmatching this closed, conservative pattern is ever recorded or echoed back to the caller.
_JOB_KEYS = ("minimax.video", "comfyui.muzik", "comfyui.video")
JOB_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
# T14-3: the polled `durum` field is from a closed set of known waiting states; anything else
# (including the raw provider string) becomes "bilinmiyor" rather than being echoed.
_WAITING_STATES = frozenset({"Preparing", "Queueing", "Processing", "pending", "queued", "running"})


def _song_parts(istek: str) -> tuple[str, str] | None:
    prompt, _, lyrics = istek.partition("\n")
    prompt, lyrics = prompt.strip(), lyrics.strip()
    if not (10 <= len(prompt) <= 300 and 10 <= len(lyrics) <= 600):
        return None
    return prompt, lyrics


class MedyaUretici:
    def __init__(self, federation: Federation, runs: RunStore, assets: AssetStore, butce: Butce | None,
                 downloader: GuvenliIndirici, monotonic: Callable[[], float] = time.monotonic) -> None:
        self.federation = federation
        self.runs = runs
        self.assets = assets
        self.butce = butce
        self.downloader = downloader
        self.monotonic = monotonic  # spec §7 budget

    def _provider_key(self, tur: str) -> str | None:
        if self.federation.configured(MINIMAX):
            return f"minimax.{tur}"
        if tur != "ses" and self.federation.configured(COMFYUI):
            return f"comfyui.{tur}"
        return None

    def uret(self, email: str, run_id: str, tur: str, istek: str, tahmin: bool = False,
             onay_belirteci: str | None = None, is_kimligi: str | None = None) -> dict[str, Any]:
        base: dict[str, Any] = {"run_id": run_id, "tur": tur, "mcp_verified": False}
        if not RUN_ID_RE.match(run_id or "") or self.runs.load(run_id) is None:
            return {**base, "status": "run_bulunamadi"}
        if tur not in TURLER:
            return {**base, "status": "gecersiz_tur", "izinli": list(TURLER)}
        istek = (istek or "").strip()
        if not istek or len(istek) > ISTEK_MAX[tur]:
            return {**base, "status": "gecersiz_istek", "sinir": ISTEK_MAX[tur]}
        if self.butce is None:
            return {**base, "status": "butce_yok"}
        # T14-5 / spec §7: one tool budget fixed once at entry and shared by every fleet call this
        # request makes, whether that is starting a job (_run) or polling one (_poll).
        deadline = self.monotonic() + TOOL_BUDGET_SECONDS
        if is_kimligi:
            return self._poll(base, email, run_id, tur, is_kimligi, deadline)
        key = self._provider_key(tur)
        if key is None:
            cov = Coverage()
            cov.skipped(MINIMAX, "anahtar yok")
            if tur != "ses":
                cov.skipped(COMFYUI, "anahtar yok")
            return {**base, "status": "atlandi", "coverage": cov.as_dict()}
        if key == "minimax.muzik" and _song_parts(istek) is None:
            return {**base, "status": "gecersiz_istek",
                    "kural": "ilk satır stil (10-300 karakter), kalan satırlar söz (10-600 karakter)"}
        amount = len(istek) if tur == "ses" else 1
        if tur == "ses":
            used = self.butce.modul_kullanimi(run_id, key)
            if used + amount > SES_MODUL_SINIRI:
                return {**base, "status": "modul_siniri", "sinir": SES_MODUL_SINIRI, "kullanilan": int(used)}
        estimate = self.butce.tahmin(key, amount)
        automatic = self.butce.otomatik_mi(key)
        provider = key.split(".", 1)[0]
        approval = {"onay_gerekli": True, "saglayici": provider, "gecerlilik_sn": ONAY_TTL_SECONDS,
                    "onay_belirteci": self.butce.onay_belirteci(email, run_id, tur, key, istek, estimate)}
        if tahmin:
            return {**base, "status": "tahmin", "tahmini_usd": estimate, "kalan_usd": self.butce.kalan(),
                    "otomatik": automatic, **({} if automatic else approval), "not": TAHMIN_NOTU}
        if not automatic:
            if onay_belirteci is None:
                return {**base, "status": "onay_gerekli", "tahmini_usd": estimate, "kalan_usd": self.butce.kalan(),
                        **approval, "not": ONAY_NOTU}
            approved = self.butce.onay_dogrula(onay_belirteci, email, run_id, tur, key, istek)
            if approved is None:
                return {**base, "status": "onay_gecersiz", "not": "Belirteç bu kullanıcı, run, tür ve istekle eşleşmiyor "
                                                                   "ya da 15 dakikası doldu; yeniden tahmin iste."}
            estimate = approved
        try:
            # T14-2: the approval token is single-use — rezerve() enforces this itself (locked,
            # keyed by the token digest), so a replayed token never reaches the provider.
            entry = self.butce.rezerve(email, run_id, key, tur, amount, estimate, onay_belirteci=onay_belirteci)
        except ButceAsildi as exc:
            return {**base, "status": "budget_exceeded", "kalan_usd": exc.kalan_usd, "tahmini_usd": exc.tahmini_usd}
        except OnayKullanildi:
            return {**base, "status": "onay_kullanildi",
                    "not": "Bu onay zaten kullanıldı; yeni tahmin ve açık onay iste."}
        return self._run(base, email, run_id, tur, key, istek, entry, estimate, deadline)

    def _run(self, base: dict[str, Any], email: str, run_id: str, tur: str, key: str, istek: str, entry: str,
             estimate: float, deadline: float) -> dict[str, Any]:
        cov = Coverage()
        provider = key.split(".", 1)[0]
        try:
            if key == "minimax.ses":
                found = self.federation.call(MINIMAX, "text_to_audio", {"text": istek}, beklenen="nesne",
                                             deadline=deadline)
            elif key == "minimax.muzik":
                prompt, lyrics = _song_parts(istek)
                found = self.federation.call(MINIMAX, "music_generation", {"prompt": prompt, "lyrics": lyrics},
                                             beklenen="nesne", deadline=deadline)
            elif key == "minimax.video":
                found = self.federation.call(MINIMAX, "generate_video",
                                             {"prompt": istek, "duration": 6, "resolution": "768P"},
                                             beklenen="nesne", deadline=deadline)
            elif key == "comfyui.muzik":
                found = self.federation.call(COMFYUI, "generate_song", {"prompt": istek}, beklenen="nesne",
                                             deadline=deadline)
            else:
                found = self.federation.call(COMFYUI, "wan_i2v", {"prompt": istek}, beklenen="nesne",
                                             deadline=deadline)
        except FederationError as exc:
            # T14-1: an ambiguous provider failure (timeout, malformed/undecodable result, ...)
            # cannot be proven un-billed, so it still counts against the cap ("belirsiz"); only a
            # clean rejection (e.g. tool_error) voids the reservation ("hata").
            self.butce.sonuclandir(entry, "belirsiz" if exc.reason in BELIRSIZ_NEDENLER else "hata")
            cov.degraded(provider, exc.reason)
            return {**base, "status": "saglayici_hatasi", "coverage": cov.as_dict()}
        if key in _JOB_KEYS:
            job_raw = found.get("task_id") or found.get("prompt_id")
            job = str(job_raw) if job_raw is not None else None
            if job is None or not JOB_ID_RE.fullmatch(job):
                # T14-3: an id the closed pattern rejects (or none at all) is a shape surprise, not
                # a job to remember — settle ambiguous (the provider may already have started
                # work) and never echo the malformed id back.
                self.butce.sonuclandir(entry, "belirsiz")
                cov.degraded(provider, "unexpected_shape")
                return {**base, "status": "saglayici_hatasi", "coverage": cov.as_dict()}
            self.butce.sonuclandir(entry, "basladi", is_kimligi=job)
            cov.hit(provider)
            return {**base, "status": "is_basladi", "is_kimligi": job, "tahmini_usd": estimate,
                    "coverage": cov.as_dict(),
                    "not": "edupedia_medya(run_id, tur, aynı istek, is_kimligi=...) ile sonucu yokla."}
        # The provider has responded (and may have billed) from here on; the reservation stays
        # "ok" even if the payload itself turns out malformed below.
        self.butce.sonuclandir(entry, "ok")
        data_field = found.get("data")
        url = data_field.get("audio") if isinstance(data_field, dict) else None
        return self._store(base, email, run_id, tur, key, url, estimate, cov, provider)

    def _store(self, base: dict[str, Any], email: str, run_id: str, tur: str, key: str, url: Any, estimate: float,
               cov: Coverage, provider: str) -> dict[str, Any]:
        try:
            if not isinstance(url, str) or not url:
                # T14-4: a shape surprise (missing/non-string url, e.g. a non-dict "data") is
                # reported the same way as any other fleet-data guard failure below.
                raise VarlikHatasi("unexpected_shape")
            data, _mime = self.downloader.indir(url)
            record = self.assets.save(run_id, data, tur, provider, f"{provider} üretimi", CREDITS[key], CREDITS[key],
                                      email)
        except VarlikHatasi as exc:
            cov.degraded(provider, exc.reason)
            return {**base, "status": "saglayici_hatasi", "coverage": cov.as_dict()}
        cov.hit(provider)
        return {**base, "status": "ok",
                "varlik": {"asset_id": record["asset_id"], "tur": tur, "mime": record["mime"], "bayt": record["bayt"],
                           "lisans": record["lisans"]},
                "slot_ornegi": SLOT[tur], "tahmini_usd": estimate, "kalan_usd": self.butce.kalan(),
                "coverage": cov.as_dict(), "not": TAHMIN_NOTU}

    def _poll(self, base: dict[str, Any], email: str, run_id: str, tur: str, job: str,
              deadline: float) -> dict[str, Any]:
        entry = self.butce.is_kaydi(run_id, email, job)
        if entry is None or entry.get("tur") != tur:
            return {**base, "status": "is_bulunamadi"}
        key, provider, cov = entry["kalem"], entry["server"], Coverage()
        try:
            if provider == MINIMAX:
                found = self.federation.call(MINIMAX, "query_video_generation", {"task_id": job}, beklenen="nesne",
                                             deadline=deadline)
                # T14-4: dict-guard every nested field the fleet returns — a shape surprise on
                # `query` means the state cannot be determined at all, so it fails immediately
                # rather than falling through to "is_suruyor" with a fabricated state.
                query_field = found.get("query")
                if not isinstance(query_field, dict):
                    cov.degraded(provider, "unexpected_shape")
                    return {**base, "status": "saglayici_hatasi", "is_kimligi": job, "coverage": cov.as_dict()}
                state = str(query_field.get("status") or "")
                file_field = found.get("file")
                inner = file_field.get("file") if isinstance(file_field, dict) else None
                url = inner.get("download_url") if isinstance(inner, dict) else None
                success, failed = state == "Success", state == "Fail"
            else:
                found = self.federation.call(COMFYUI, "get_job", {"prompt_id": job}, beklenen="nesne",
                                             deadline=deadline)
                state = str(found.get("status") or "")
                outputs = found.get("outputs")
                outputs = outputs if isinstance(outputs, list) else []
                first = outputs[0] if outputs else None
                url = first.get("url") if isinstance(first, dict) else None
                success, failed = state == "completed", state in ("failed", "error", "cancelled")
        except FederationError as exc:
            cov.degraded(provider, exc.reason)
            return {**base, "status": "saglayici_hatasi", "is_kimligi": job, "coverage": cov.as_dict()}
        if failed:
            self.butce.sonuclandir(entry["id"], "hata")
            return {**base, "status": "is_basarisiz", "is_kimligi": job}
        if not success:
            durum = state if state in _WAITING_STATES else "bilinmiyor"
            return {**base, "status": "is_suruyor", "is_kimligi": job, "durum": durum}
        result = self._store(base, email, run_id, tur, key, url, float(entry["tahmini_usd"]), cov, provider)
        if result["status"] == "ok":
            self.butce.sonuclandir(entry["id"], "ok")
        return result
