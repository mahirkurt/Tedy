"""B6: tek cevap denetiminin saf kararları ve çevrimdışı değerlendirme puanı."""
from __future__ import annotations

import json
import re
from typing import Any


DENETIM_MODEL = "claude-haiku-4-5"
UZUN_CEVAP = 800
KURAL_SINIRI = 1500
DENETIM_KAYNAK = 8
DENETIM_MAX_TOKENS = 2000
DENETIM_TIMEOUT_S = 30
DENETIM_ISTEMI = """Sen bir denetçisin. Okura yazma; yalnız bir JSON nesnesi yaz.
kaynak: snippet kaynağın yalnız kısaltılmış başıdır; bir bilginin snippet'te görünmemesi tek başına ciddi değildir. [Sn] cümlesi aynı numaralı snippet ile açıkça çelişiyorsa ya da cümledeki kazanım kodu veya sayfa numarası o kaynağın label'ında ve snippet'inde hiç yoksa ciddi. İşaretsiz genel bilgi ciddi değildir.
seviye: anlatım 7. sınıf içindir. Üniversite terimi ya da adımı atlayan çözüm ciddi.
ogretmen: kurallar null ise bu bakış yoktur, sorun listesine ogretmen yazma. Varsa yalnız ipucu verip çözümü saklamak ya da ödevi teslim metni veya cevap anahtarı diye yazmak ciddi. Benzer alıştırma cümlesinin yokluğu tek başına ciddi değildir.
hitap: okur ogrenci ise sen; Işık üçüncü şahıs ise ciddi. okur aile ya da bilinmiyor ise siz ve Işık üçüncü şahıs. İkisi birden ciddi.
Ciddi değilse {"ciddi": false}. Ciddi ise {"ciddi": true, "sorun": ["kaynak"], "cevap": "bütün cevap"}. cevap okura gösterilecek düzeltilmiş tam cevaptır: taslağın [S] işaretlerini korur, taslağın yerine geçer, sonuna eklenmez. cevap'a denetim notu, eleştiri ya da snippet sözü yazma. Yeni [S] numarası uydurma. Snippet'te olmayan olgu ekleme."""


_ATIF = re.compile(r"\[S\d+\]")
# Yalnız bir denetçinin yazacağı ifadeler; 7. sınıfa yazılmış bir cevapta geçmez. Ölçüldü 2026-10-05:
# Haiku düzeltilmiş cevap yerine "Snippet'ler eksik … kaynak olarak kullanılamaz … kütüphaneden
# silinmelidir" yazdı ve bu not Fen cevabının yerine okura gösterildi.
_DENETCI_DILI = ("snippet", "kaynak olarak kullanılamaz", "kütüphaneden", '"ciddi"')


def _denetci_dili(metin: str) -> bool:
    from src.assistant_core import turkce_kucult_katla

    katli = turkce_kucult_katla(metin)
    return any(turkce_kucult_katla(ifade) in katli for ifade in _DENETCI_DILI)


def denetim_gerekli(ogretmen: str, cevap: str, hata_metinleri: list[str]) -> str | None:
    """None çağrı demektir; atlanan cevap için yalnız sabit neden döner."""
    if cevap in hata_metinleri:
        return "hata_cevabi"
    if ogretmen == "genel" and len(cevap) < UZUN_CEVAP:
        return "genel_kisa"
    return None


def ogretmen_kurallari(govde: str) -> str:
    """Sınırlar bütünüyle korunur; yalnız Ders akışı bölümü kısaltılır."""
    basliklar = list(re.finditer(r"(?m)^## [^\n]+", govde))
    bolumler = {}
    for i, baslik in enumerate(basliklar):
        son = basliklar[i + 1].start() if i + 1 < len(basliklar) else len(govde)
        bolumler[baslik.group().strip()] = govde[baslik.start():son].strip()
    return "\n\n".join(parca for parca in (
        bolumler.get("## Sınırlar", ""),
        bolumler.get("## Ders akışı", "")[:KURAL_SINIRI],
    ) if parca)


def denetim_oku(ham: str, *, ogretmen_bakisi: bool = True) -> dict[str, Any]:
    """İlk JSON çitini ya da çıplak JSON'u doğrular; ham içerik hataya taşınmaz."""
    if not isinstance(ham, str):
        raise ValueError("denetim biçimi")
    if "```" in ham:
        cit = re.search(r"```(?:json)?\s*(.*?)```", ham, re.DOTALL)
        if not cit:
            raise ValueError("denetim biçimi")
        ham = cit.group(1)
    try:
        karar = json.loads(ham)
    except json.JSONDecodeError:
        raise ValueError("denetim biçimi") from None
    if not isinstance(karar, dict) or type(karar.get("ciddi")) is not bool:
        raise ValueError("denetim biçimi")
    if not karar["ciddi"]:
        return {"ciddi": False}
    izinli = {"kaynak", "seviye", "hitap"}
    if ogretmen_bakisi:
        izinli.add("ogretmen")
    ham_sorun = karar.get("sorun")
    if not isinstance(ham_sorun, list):
        raise ValueError("denetim biçimi")
    sorun = list(dict.fromkeys(s for s in ham_sorun if isinstance(s, str) and s in izinli))
    cevap = karar.get("cevap")
    if not sorun or not isinstance(cevap, str) or not cevap:
        raise ValueError("denetim biçimi")
    return {"ciddi": True, "sorun": sorun, "cevap": cevap}


def denetim_uygula(cevap: str, karar: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Doğrulanmış karar, taslağı en çok bir kez bütün olarak değiştirir."""
    meta = {"durum": "gecti", "neden": None,
            "sorun": karar.get("sorun", []), "model": DENETIM_MODEL}
    if not karar["ciddi"]:
        return cevap, meta
    yeni = karar["cevap"].strip()
    if not yeni or yeni == cevap.strip():
        meta.update(durum="hata", neden="bos" if not yeni else "ayni")
        return cevap, meta
    # Değişim, taslağı okura göstermekten daha kötü olabilir: yerine geçen metin cevap değil de
    # denetçinin notuysa, ya da kaynak/seviye/hitap düzeltmesi taslağın bütün atıflarını düşürüyorsa
    # taslak kalır. ogretmen düzeltmesi (cevap anahtarı yerine ret) atıfsız olabilir.
    if _denetci_dili(yeni):
        meta.update(durum="hata", neden="denetim_dili")
        return cevap, meta
    if "ogretmen" not in meta["sorun"] and _ATIF.search(cevap) and not _ATIF.search(yeni):
        meta.update(durum="hata", neden="atif_kaybi")
        return cevap, meta
    meta["durum"] = "duzeltildi"
    return yeni, meta


def puanla(soru: dict[str, Any], cevap: str, cagrilar: list[dict[str, Any]],
           atiflar: list[dict[str, Any]]) -> dict[str, Any]:
    from src.assistant_core import turkce_kucult_katla

    araclar = list(dict.fromkeys(c["name"] for c in cagrilar if c.get("name")))
    kaynak = turkce_kucult_katla(soru["kaynak"])
    kaynak_tamam = any(
        kaynak in turkce_kucult_katla(str(metin))
        for atif in atiflar
        for metin in (atif.get("label", ""), atif.get("snippet", ""),
                      (atif.get("locator") or {}).get("tool", ""))
    )
    katli_cevap = turkce_kucult_katla(cevap)
    eksik = [nokta for nokta in soru["noktalar"]
             if turkce_kucult_katla(nokta) not in katli_cevap]
    return {"arac_tamam": soru["arac"] in araclar, "kaynak_tamam": kaynak_tamam,
            "nokta_tamam": not eksik, "eksik_noktalar": eksik,
            "cagrilan_araclar": araclar}


def sorgu_dar(dusen: list[str], noktalar: list[str]) -> bool:
    from src.assistant_core import turkce_kucult_katla

    nokta_tokenleri = set(re.findall(r"\w+", turkce_kucult_katla(" ".join(noktalar))))
    dusen_tokenler = set(re.findall(r"\w+", turkce_kucult_katla(" ".join(dusen))))
    return bool(nokta_tokenleri & dusen_tokenler)
