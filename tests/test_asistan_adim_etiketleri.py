"""Carbon AI asistanında her araç çağrısı okura bir adım olarak görünür (dashboard/src/asistan/olayEslemesi.ts
ARAC_ETIKETI). Etiketsiz araç "Kaynaklar taranıyor" diye genel bir adımla görünür; var olmayan araca etiket de
eskimiş bir addır (alıştırma aracı 'alistirma_hazirla' sanılıyordu, gerçek adı 'alistirma_olustur')."""
import re
from pathlib import Path

from src import assistant_kitaplar, assistant_modules, assistant_tools

ROOT = Path(__file__).resolve().parents[1]


def _arac_adlari() -> set[str]:
    kaynak = (ROOT / "src" / "assistant_tools.py").read_text(encoding="utf-8")
    adlar = set(assistant_tools.TOOL_ALLOWLIST)
    adlar |= {v for k, v in vars(assistant_tools).items()
              if isinstance(v, str) and (k.endswith("_TOOL") or k in ("ODEV_BELGE", "ODEV_TAMAMLA"))}
    adlar |= set(assistant_tools._HAFIZA_ARACLARI)
    adlar |= set(re.findall(r'"name":\s*"([a-z_]+)"', kaynak))
    adlar |= {assistant_kitaplar.TOOL_NAME, assistant_modules.TOOL_NAME}
    return adlar


def _etiketler() -> set[str]:
    ts = (ROOT / "dashboard" / "src" / "asistan" / "olayEslemesi.ts").read_text(encoding="utf-8")
    blok = ts[ts.index("ARAC_ETIKETI"):ts.index("VARSAYILAN_ADIM")]
    return set(re.findall(r"(\w+):\s*'", blok))


def test_her_aracin_kendi_adim_etiketi_var_ve_eskimis_etiket_yok():
    adlar, etiketler = _arac_adlari(), _etiketler()
    assert len(adlar) >= 38, sorted(adlar)          # yüzey daralırsa test boşa geçmesin
    assert sorted(adlar - etiketler) == []
    assert sorted(etiketler - adlar) == []
