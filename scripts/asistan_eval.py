"""Altın soru değerlendirmesi; ücretli koşu yalnız açık --onayla ile başlar."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SORULAR = Path(__file__).resolve().parents[1] / "src/assistant_eval/sorular.json"


def sorulari_yukle(yol: Path = SORULAR) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))["dersler"]


def dusen_tokenleri(soru: str) -> list[str]:
    from src.assistant_core import turkce_kucult_katla
    from src.assistant_tools import _sorguya

    kalan = {turkce_kucult_katla(token) for token in _sorguya(soru).split()}
    return list(dict.fromkeys(
        turkce_kucult_katla(token)
        for token in soru.replace("?", "").replace("!", "").split()
        if turkce_kucult_katla(token) not in kalan
    ))


def sonuc_yaz(kok: Path, satirlar: list[dict], sha: str, *,
              simdi: datetime | None = None, calistir_sayisi: int | None = None,
              model: str = "") -> Path:
    from src.assistant_denetim import DENETIM_MODEL
    from src.json_utils import atomic_json_dump

    simdi = (simdi or datetime.now(timezone.utc)).astimezone(timezone.utc)
    damga = simdi.strftime("%Y%m%dT%H%M%SZ")
    kok = Path(kok)
    kok.mkdir(parents=True, exist_ok=True)
    sira = 1
    while True:
        dizin = kok / (damga if sira == 1 else f"{damga}-{sira}")
        try:
            dizin.mkdir()
        except FileExistsError:
            sira += 1
            continue
        break
    sonuc = {
        "surum": "1", "zaman": simdi.isoformat().replace("+00:00", "Z"),
        "model": model, "denetim_model": DENETIM_MODEL,
        "sorular_sha256": sha, "sorular": satirlar,
        "ozet": {
            "soru": len(satirlar) if calistir_sayisi is None else calistir_sayisi,
            **{ad: sum(satir[ad] is True for satir in satirlar)
               for ad in ("arac_tamam", "kaynak_tamam", "nokta_tamam")},
        },
    }
    yol = dizin / "sonuc.json"
    atomic_json_dump(sonuc, str(yol))
    return yol


def kos(*, runtime=None, kok: Path | None = None) -> Path:
    from src.assistant_core import AssistantRuntime
    from src.assistant_denetim import puanla, sorgu_dar

    proje = Path(__file__).resolve().parents[1]
    runtime = runtime if runtime is not None else AssistantRuntime(proje)
    dersler = sorulari_yukle()
    sha = hashlib.sha256(SORULAR.read_bytes()).hexdigest()
    satirlar = []
    model = runtime.llm.model
    for ders, sorular in dersler.items():
        for soru in sorular:
            try:
                sonuc = runtime.chat(
                    messages=[{"role": "user", "content": soru["soru"]}],
                    ogretmen=ders, okur="ogrenci", etkilesimli=False,
                )
            except Exception:
                # Bir sorunun hatası diğer on birini düşürmez; hata metni kayda girmez.
                sonuc = {"answer": "", "citations": [], "meta": {
                    "tool_calls": [], "denetim": {
                        "durum": "hata", "neden": "cagri", "sorun": [], "model": None,
                    },
                }}
            meta = sonuc["meta"]
            model = meta.get("model") or model
            dusen = dusen_tokenleri(soru["soru"])
            satirlar.append({
                "id": soru["id"], "ogretmen": ders,
                **puanla(soru, sonuc["answer"], meta["tool_calls"], sonuc["citations"]),
                "denetim": meta["denetim"], "sorgu_dar": sorgu_dar(dusen, soru["noktalar"]),
                "dusen_tokenler": dusen, "cevap": sonuc["answer"],
            })
    return sonuc_yaz(kok if kok is not None else proje / "output/asistan_eval",
                     satirlar, sha, model=model)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--onayla" not in argv:
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onayla", action="store_true", required=True)
    parser.parse_args(argv)
    kos()
    return 0


if __name__ == "__main__":
    if "--onayla" in sys.argv[1:]:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from src.env_loader import load_env

        load_env()
    raise SystemExit(main(sys.argv[1:]))
