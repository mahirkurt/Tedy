"""Alt metnin dayanağı (Modül Tasarım Kanunu M3.6, M3.7; KB-10, 2026-10-23).

Yazarın alt metnindeki özel adlar ve sayılar figürün kendi açıklamasında (kitap figürünün caption'ı,
Pexels açıklaması, üretim istemi) ya da çerçeve sayfalarının metninde geçer. Geçmeyen ad ya da sayı bir
uydurma işaretidir (ölçüldü: bir alt metin KAAN'ı "F-35" diye adlandırıyordu). Kanunun ölçütü "kaynakta
geçmeyen her büyük harfli sözcük ya da rakam dizisi"dir; Türkçede cümle başı büyük harf dil bilgisidir,
bu yüzden cümle başındaki sözcük yalnız özel ad olduğu belliyse (kesme işaretli ek ya da tümü büyük
kısaltma) sayılır. Saf işlevler; ağ yok. `derle_araci` run'ın sayfa metni ve varlık kaydıyla çağırır.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

from src.mcp_server.derleme import GomuluVarlik, duzle

_HARF = "A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû"
# Sözcük: harf/rakam öbekleri, kısa çizgi ya da ondalık ayırıcıyla bağlı ("F-35", "3,5"), isteğe bağlı
# kesme işaretli ek ("Ankara'ya", "KAAN’ın").
_SOZCUK_RE = re.compile(rf"[{_HARF}0-9]+(?:[-.,][{_HARF}0-9]+)*(?:['’][{_HARF}]+)?")
_CUMLE_SONU = ".!?…"
_BUYUK = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZÂÎÛQWX"
_SAPKA = str.maketrans({"â": "a", "î": "i", "û": "u", "’": "'"})


def katla(metin: str) -> str:
    """Türkçe küçültme (I→ı, İ→i), şapka ve tipografik kesme sadeleşir; aynı ad iki yazımda eşleşir."""
    metin = unicodedata.normalize("NFC", metin).replace("I", "ı").replace("İ", "i").lower()
    return metin.translate(_SAPKA)


def _sayi(metin: str) -> str:
    return re.sub(r"(?<=\d)[.,](?=\d)", ".", metin)


def _cumle_basi(alt: str, bas: int) -> bool:
    onceki = alt[:bas].rstrip(" \t\n\"'“”‘’«»(")
    return onceki == "" or onceki[-1] in _CUMLE_SONU


def dayanaksiz_adlar(alt: str, kaynak: str) -> list[str]:
    """Alt metinde geçip kaynakta geçmeyen özel adlar ve sayılar, ilk görünüş sırasıyla (tekrarsız).

    Ad kaynakta bir sözcüğün başında geçmelidir (ek ve bileşik ad serbest: "Ankara" ↔ "Ankara'dan",
    "Kemal" ↔ "Kemalpaşa"); sözcük içi geçiş sayılmaz. Rakam taşıyan öbek kaynakta aynen geçer
    ("1919" "19190" değildir; "3,5" ile "3.5" aynıdır).
    """
    kaynak_k = _sayi(katla(kaynak))
    bulunan: list[str] = []
    for m in _SOZCUK_RE.finditer(alt):
        kok = re.split(r"['’]", m.group(0), maxsplit=1)[0]
        ekli = kok != m.group(0)
        if any(c.isdigit() for c in kok):
            desen = r"(?<![0-9a-zçğıöşü])" + re.escape(_sayi(katla(kok))) + r"(?![0-9])"
        elif kok[0] in _BUYUK:
            kisaltma = len(kok) >= 2 and kok.upper() == kok and not kok.isdigit()
            if _cumle_basi(alt, m.start()) and not (ekli or kisaltma):
                continue
            desen = r"(?<![0-9a-zçğıöşü])" + re.escape(katla(kok))
        else:
            continue
        if not re.search(desen, kaynak_k) and kok not in bulunan:
            bulunan.append(kok)
    return bulunan


def varlik_kaynagi(varlik: GomuluVarlik, sayfa_metni: str) -> str:
    """Bir varlığın alt metninin dayanabileceği metin: yalnız kitabın kendi metni — figür altı yazısı (Maarif
    `nearby_text`), kitaptaki etiketi ve run'ın çerçeve sayfaları. Betim (Maarif `caption` = VLM, Pexels
    açıklaması, üretim istemi) ve eski kayıtların 200 karakterlik `alt`'ı dayanak değildir: ölçüldü, figür 4189'un
    VLM betimi KAAN'ı "F-35" diye adlandırıyor (son inceleme, Kritik 1)."""
    return "\n".join(x for x in (varlik.kitap_altyazisi, varlik.etiket, sayfa_metni) if x)


def alt_metin_dayanagi(data: Mapping[str, Any], varliklar: Mapping[str, GomuluVarlik],
                       sayfa_metni: str) -> tuple[list[str], list[str]]:
    """(hatalar, uyarilar). Dayanaksız ad ya da sayı: gerekçe yoksa hata, `alt_gerekce` varsa uyarı.
    Kitap figürünün etiketi (ör. "Görsel 1.30") altyazıda yoksa uyarı (Kanun M3.7: kitaptaki adıyla)."""
    hatalar: list[str] = []
    uyarilar: list[str] = []
    refs = (data.get("meta") or {}).get("assets") or []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            continue
        varlik = varliklar.get(ref.get("asset_id"))
        if varlik is None or varlik.tur != "image":
            continue
        yol = f"meta.assets[{index}]"
        alt = duzle(ref["alt"]) if isinstance(ref.get("alt"), str) else ""
        eksik = dayanaksiz_adlar(alt, varlik_kaynagi(varlik, sayfa_metni)) if alt else []
        if eksik:
            adlar = ", ".join(f"«{a}»" for a in eksik)
            gerekce = ref.get("alt_gerekce")
            if isinstance(gerekce, str) and duzle(gerekce):
                uyarilar.append(f"{yol}.alt: {adlar} kitabın metninde (figür altı yazısı, etiket, çerçeve "
                                f"sayfaları) geçmiyor; gerekçe: {duzle(gerekce)}")
            else:
                hatalar.append(f"{yol}.alt: {adlar} kitabın metninde (figür altı yazısı, etiket, çerçeve sayfaları) "
                               "geçmiyor; adı ve sayıyı kitaptaki gibi yaz ya da gerekçeyi "
                               f"{yol}.alt_gerekce'ye yaz (Kanun M3.6)")
        etiket = duzle(varlik.etiket or "")
        baslik = ref.get("baslik")
        if etiket and isinstance(baslik, str) and katla(etiket) not in katla(duzle(baslik)):
            uyarilar.append(f"{yol}.baslik kitaptaki etiketi taşımıyor («{etiket}»); altyazı figürü kitaptaki "
                            "adıyla anar (Kanun M3.7)")
    return hatalar, uyarilar
