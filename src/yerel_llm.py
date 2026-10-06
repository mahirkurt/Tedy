"""TEDY'nin evdeki dil modeli: mbp-node'daki Gemma 4 e4b, ai-hub politika proxy'si üzerinden.

Yalnız iki tür işte kullanılır (2026-10-06):
- Okuru bekletmeyen arka plan işleri — sohbet başlığı ve eski turların özeti. Kişisel sohbet metni
  evden çıkmaz; Haiku'ya yalnız yerel model düşerse gider.
- Başka yol kalmadığında: Claude'a ulaşılamazsa asistan susmak yerine yerel modelle, kaynaksız
  olduğunu açıkça söyleyen kısa bir yedek cevap verir.

Ana cevap Claude'da kalır: Gemma CPU'da saniyede ~7 token yazar, araç kullanmaz ve müfredat/kitap
doğruluğu Sonnet düzeyinde değildir. Proxy (`ollama-policy-proxy`, mbp :11435) think=false'u ve
mbp'de tek sohbet modeli kuralını uygular; bu yüzden işler tek kuyrukta sırayla çalışır.
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

VARSAYILAN_TOKEN = 700
BASLIK_MAX = 60


class YerelHata(RuntimeError):
    """The local model gave no usable answer. The message stays internal."""


@dataclass(frozen=True)
class YerelAyar:
    acik: bool
    url: str
    model: str


def ayarlar() -> YerelAyar:
    """Off unless ASSISTANT_YEREL_LLM=1 (live .env), so tests and ad-hoc runtimes never reach mbp."""
    return YerelAyar(
        acik=os.environ.get("ASSISTANT_YEREL_LLM", "").strip() == "1",
        url=(os.environ.get("ASSISTANT_YEREL_LLM_URL", "").strip() or "http://mbp.lan:11435").rstrip("/"),
        model=os.environ.get("ASSISTANT_YEREL_LLM_MODEL", "").strip() or "gemma4-e4b-cpu",
    )


def _istek(url: str, govde: dict[str, Any], zaman_asimi: float) -> Iterator[str]:
    """NDJSON lines of an Ollama /api/chat stream. Module attribute so tests can replace it."""
    with requests.post(url, json=govde, stream=True, timeout=(5, zaman_asimi)) as yanit:
        yanit.raise_for_status()
        for satir in yanit.iter_lines(decode_unicode=True):
            if satir:
                yield satir


def sohbet(mesajlar: list[dict[str, str]], *, ayar: YerelAyar, sistem: str | None = None,
           on_delta: Callable[[str], None] | None = None, max_token: int = VARSAYILAN_TOKEN,
           zaman_asimi: float = 120.0) -> str:
    """One streamed answer. Raises YerelHata when off, unreachable, cut short or empty."""
    if not ayar.acik:
        raise YerelHata("kapalı")
    govde = {
        "model": ayar.model, "stream": True, "think": False,
        "options": {"num_predict": max_token, "num_ctx": 8192},
        "messages": ([{"role": "system", "content": sistem}] if sistem else []) + list(mesajlar),
    }
    parcalar: list[str] = []
    bitti = False
    try:
        for satir in _istek(f"{ayar.url}/api/chat", govde, zaman_asimi):
            veri = json.loads(satir)
            parca = (veri.get("message") or {}).get("content") or ""
            if parca:
                parcalar.append(parca)
                if on_delta is not None:
                    on_delta(parca)
            if veri.get("done"):
                bitti = True
                break
    except YerelHata:
        raise
    except Exception as exc:  # noqa: BLE001 — network, HTTP or a malformed line
        raise YerelHata(type(exc).__name__) from exc
    metin = "".join(parcalar).strip()
    if not bitti or not metin:
        raise YerelHata("yarım" if not bitti else "boş")
    return metin


# One worker: mbp keeps a single chat model resident, so local jobs queue rather than compete.
_havuz = ThreadPoolExecutor(max_workers=1, thread_name_prefix="yerel-llm")


def arka_planda(is_: Callable[..., Any], *args: Any) -> Future:
    """Run a job after the reader already has the answer. A failure is logged, never raised."""
    def sar() -> None:
        try:
            is_(*args)
        except Exception as exc:  # noqa: BLE001
            logger.warning("yerel arka plan işi başarısız: %s", type(exc).__name__)
    return _havuz.submit(sar)


def baslik_temizle(ham: str) -> str | None:
    """First non-empty line, without Markdown, quotes, a "Başlık:" label or a final full stop;
    None when nothing short enough is left."""
    for satir in (ham or "").splitlines():
        s = re.sub(r"^[#>*\-\s]+|\*\*|__|`", "", satir).strip()
        s = re.sub(r"^başlık\s*:\s*", "", s, flags=re.IGNORECASE).strip()
        s = s.strip("\"'“”‘’").rstrip(".").strip()
        if s:
            return s if len(s) <= BASLIK_MAX else None
    return None
