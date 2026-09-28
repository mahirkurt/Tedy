"""7. sınıf ünite/tema ve kazanım haritası — öğretmen skill'lerinin references/unite-haritasi.md'si.

Canlı müfredat veritabanından (maarif MCP'nin kendi korpusu, sürüm 1.6) üretilir; elle yazılmaz,
elle düzenlenmez. Veritabanı YALNIZ şu URI ile, salt okunur ve değişmez kipte açılır:

    file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1

(Makinede sqlite3 komut satırı aracı kurulu değil; aynı URI Python'un sqlite3 modülüyle açılır.)

Kullanım:
    .venv/bin/python scripts/skill_unite_haritasi.py matematik > src/assistant_skills/matematik/references/unite-haritasi.md

Sayfa aralıkları ve başlık desenleri 2026-09-27'de programların kendi sayfalarında ölçüldü
(ör. Ortaokul Matematik programında "7. SINIF" s.115, "8. SINIF" s.173).
"""
from __future__ import annotations

import re
import sqlite3
import sys

URI = "file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1"

# ad: (ders adı, subject slug, program document id, 7. sınıf sayfa aralığı, başlık deseni, kazanım kodu deseni)
DERSLER = {
    "matematik": ("Matematik", "ortaokul-matematik-dersi", 24, (115, 172),
                  r"^\s*(\d+)\.\s*TEMA:\s*(.+)$", r"^MAT\.7\.(\d+)\.(\d+)$"),
    "fen": ("Fen Bilimleri", "fen-bilimleri-dersi", 54, (146, 183),
            r"^\s*(\d+)\.\s*ÜNİTE:\s*(.+)$", r"^FB\.7\.(\d+)\.(\d+)$"),
    "sosyal": ("Sosyal Bilgiler", "sosyal-bilgiler-dersi", 100, (93, 122),
               r"^\s*(\d+)\.\s*ÖĞRENME ALANI:\s*(.+)$", r"^SB\.7\.(\d+)\.(\d+)$"),
    "turkce": ("Türkçe", "ortaokul-turkce-dersi", 51, (126, 161),
               r"^\s*(\d+)\.\s*TEMA:\s*(.+)$", r"^(T\.[DOKY]|DYS\.(?:DO|KY))\.7\.(\d+)$"),
}
BUYUK = "A-ZÇĞİÖŞÜ"
KUCUK = "a-zçğıöşüâîû"
# Program PDF'lerinin metin katmanındaki harf aralığı bozulmaları (ölçüldü 2026-09-27).
OCR_DUZELTME = {"SOSY AL": "SOSYAL", "DÜNY A": "DÜNYA", "HAY ATIMIZDAKİ": "HAYATIMIZDAKİ",
                "YAŞAY AN": "YAŞAYAN", "KÜL TÜRÜ": "KÜLTÜRÜ"}
# Satır sonu tirelemesiyle karışan GERÇEK bileşik sözcükler: 'yer- yön' (satır kırığı) genel
# tireleme temizliğinde tiresiz 'yeryön'e döner; bu, 'yer-yön' bileşiğini bozar (ölçüldü,
# DYS.DO.7.6, korpus 1.6). temizle() önce genel kırığı giderir, sonra bu sözcüğü düzeltir.
BILESIK_KORUMA = {"yeryön": "yer-yön"}
TURKCE_BECERILER = {"T.D": "Dinleme/İzleme", "T.O": "Okuma", "T.K": "Konuşma", "T.Y": "Yazma",
                    "DYS.DO": "Dil yapıları — dinleme/okumada belirleme",
                    "DYS.KY": "Dil yapıları — konuşma/yazmada kullanma"}


def temizle(metin: str) -> str:
    """Satır sonu tirelemesi ve fazla boşluk: 'yapa - bilme' -> 'yapabilme'.

    Gerçek bileşik sözcüklerin (ör. 'yer-yön') tiresi bu genel temizlikte yanlışlıkla
    silinirse BILESIK_KORUMA ile geri konur.
    """
    metin = " ".join(metin.split())
    metin = re.sub(rf"(?<=[{KUCUK}])\s?-\s+(?=[{KUCUK}])", "", metin)
    for yanlis, dogru in BILESIK_KORUMA.items():
        metin = metin.replace(yanlis, dogru)
    return metin


def ana_cumle(metin: str) -> str:
    """Kazanımın ana ifadesi: ' a) ' ile başlayan süreç bileşenlerinden önceki kısım."""
    return re.split(r"\s[a-zç]\)\s", temizle(metin), maxsplit=1)[0].strip()


def _tek_bilme_govdesi(temiz: str) -> bool:
    """Aday satır büyük harfle başlamalı, açık parantezle (bir açıklama metninin ortasından
    kesilmiş) bitmemeli ve tam olarak bir '-bilme' fıkrası taşımalı. '\\bbilme\\b' sınırı
    kullanılır: 'bilmediği' gibi rastlantısal iç geçişler (fiil değil) sayılmaz, yalnız
    sözcük SONUNDAKİ '-bilme'ler ('tartışabilme,', 'edebilme') sayılır."""
    return bool(temiz) and bool(re.match(f"[{BUYUK}]", temiz)) and not temiz.endswith("(") \
        and len(re.findall(r"bilme\b", temiz)) == 1


def baslik_ifadesi(metin: str) -> str | None:
    """Bir 'heading' (başlık) satırının kendisi tek bir '-bilme' fıkrası mı: kabul edilirse o
    metni döner. Başka bir başlıkla yapışık satırlar ('... değerlendirebilme Okuma' gibi, iki
    ayrı başlığın korpusta yan yana düşmesinden) ya da uçtan kesik satırlar reddedilir —
    bunlar 'bilme' ile bitmediği için ('Okuma' ile bitiyor) elenir."""
    temiz = temizle(metin).strip().rstrip(".")
    if not _tek_bilme_govdesi(temiz) or not temiz.endswith("bilme"):
        return None
    return temiz


def aciklama_ifadesi(metin: str) -> str | None:
    """Bir 'outcome' (açıklama) satırından ana ifadeyi çıkarır: süreç bileşenlerinden ayırır,
    sonra ilk '-bilme' sınırına keser. Birden çok fıkra taşıyan (ör. 'tartışabilme, ...
    değerlendirebilme (') ya da açık parantezle kesilen satırlar — bunlar tek bir kazanımın
    değil, birkaçının ortak açıklaması — reddedilir."""
    temiz = temizle(metin).strip()
    if not _tek_bilme_govdesi(temiz):
        return None
    eslesme = re.match(r"^(.*?bilme)\b", ana_cumle(metin))
    return eslesme.group(1) if eslesme else None


def baslik_yaz(ad: str) -> str:
    """'EVİMİZ DÜNY A' -> 'Evimiz Dünya'; 've' küçük kalır."""
    for bozuk, dogru in OCR_DUZELTME.items():
        ad = ad.replace(bozuk, dogru)
    ad = re.sub(r"\s*\(\d\)\s*$", "", ad).strip()
    kelimeler = []
    for i, k in enumerate(ad.replace("İ", "i").replace("I", "ı").lower().split()):
        if i and k == "ve":
            kelimeler.append(k)
        else:
            kelimeler.append({"i": "İ", "ı": "I"}.get(k[0], k[0].upper()) + k[1:])
    return " ".join(kelimeler)


def kod_sirasi(kod: str) -> list:
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in kod.split(".")]


def main(ad: str) -> None:
    ders, slug, belge, (ilk, son), baslik_deseni, kod_deseni = DERSLER[ad]
    con = sqlite3.connect(URI, uri=True)
    surum = con.execute("SELECT value FROM manifest WHERE key = 'corpus_version'").fetchone()[0]
    program = con.execute("SELECT title FROM document WHERE id = ?", (belge,)).fetchone()[0]

    temalar: list[tuple[int, str, int]] = []
    for sayfa, metin in con.execute(
            "SELECT page_no, text FROM document_page WHERE document_id = ? "
            "AND page_no BETWEEN ? AND ? ORDER BY page_no", (belge, ilk, son)):
        for satir in metin.splitlines():
            m = re.match(baslik_deseni, satir)
            if m and not any(t[0] == int(m.group(1)) for t in temalar):
                temalar.append((int(m.group(1)), baslik_yaz(m.group(2)), sayfa))
    temalar.sort()

    kodlar: dict[str, list[tuple[int, str]]] = {}
    for kod, sayfa, metin in con.execute(
            "SELECT lo.code, lo.page_no, lo.text FROM learning_outcome lo "
            "JOIN subject s ON s.id = lo.subject_id "
            "WHERE s.slug = ? AND lo.grade_label = '7.Sınıf' AND lo.fragment_type = 'outcome' "
            "ORDER BY lo.page_no, lo.id", (slug,)):
        if re.match(kod_deseni, kod or ""):
            kodlar.setdefault(kod, []).append((sayfa, metin))

    # Türkçe'de bazı 'T.' kodlarının tam ifadesi 'outcome' parçasında değil, 'heading'
    # (başlık) satırında temiz duruyor — ör. T.Y.7.1'in outcome satırı iki fıkralı bir
    # açıklama metninin ortasından kesik ("... tartışabilme, ... değerlendirebilme (");
    # heading satırı ise tek başına doğru ifade ("Yazma sürecini yönetebilme"). Yalnız
    # Türkçe'de sorgulanır (diğer derslerin kod şeması bu ayrıma ihtiyaç duymaz).
    basliklar: dict[str, list[tuple[int, str]]] = {}
    if ad == "turkce":
        for kod, sayfa, metin in con.execute(
                "SELECT lo.code, lo.page_no, lo.text FROM learning_outcome lo "
                "JOIN subject s ON s.id = lo.subject_id "
                "WHERE s.slug = ? AND lo.grade_label = '7.Sınıf' AND lo.fragment_type = 'heading' "
                "ORDER BY lo.page_no, lo.id", (slug,)):
            if re.match(kod_deseni, kod or ""):
                basliklar.setdefault(kod, []).append((sayfa, metin))

    print(f"# 7. sınıf {ders} — tema ve kazanım haritası\n")
    print(f"<!-- kaynak: {URI} · subject={slug} · program document_id={belge} · "
          f"sayfa {ilk}-{son} · corpus_version={surum} -->\n")
    print(f"Kaynak: MEB müfredat korpusu {surum}, {program}, s.{ilk}–{son}. Bu dosya "
          f"`scripts/skill_unite_haritasi.py {ad}` çıktısıdır; elle düzenlenmez. Bir kazanımın "
          "tam metni ve süreç bileşenleri (a, b, c…) için kodu `kazanim_ara` ile ara.\n")
    print("## Temalar / üniteler\n")
    for no, ad_, sayfa in temalar:
        print(f"{no}. {ad_} (program s.{sayfa})")

    if ad != "turkce":
        print("\n## Kazanımlar")
        onceki = None
        for kod in sorted(kodlar, key=kod_sirasi):
            tema = int(re.match(kod_deseni, kod).group(1))
            if tema != onceki:
                ad_ = next((t[1] for t in temalar if t[0] == tema), "?")
                print(f"\n### {tema}. {ad_}\n")
                onceki = tema
            sayfa, metin = kodlar[kod][0]
            print(f"- **{kod}** — {ana_cumle(metin)} (program s.{sayfa})")
        return

    print("\nTürkçe programında kazanımlar temaya göre değil, beceri alanına göre kodlanır; "
          "aynı beceri her temada yeniden işlenir.")
    print("\n## Kazanımlar (beceri alanına göre)")
    for onek, baslik in TURKCE_BECERILER.items():
        grup = sorted((k for k in kodlar if k.startswith(onek + ".")), key=kod_sirasi)
        if not grup:
            continue
        print(f"\n### {baslik}\n")
        yalniz_kod = []
        for kod in grup:
            if onek.startswith("T."):
                # Başlık satırından temiz bir tek-fıkra ifadesi varsa onu tercih et; yoksa
                # açıklama satırından çıkar.
                adaylar = [f for f in (baslik_ifadesi(m) for _, m in basliklar.get(kod, []))
                           if f]
                if not adaylar:
                    adaylar = [f for f in (aciklama_ifadesi(m) for _, m in kodlar.get(kod, []))
                               if f]
            else:
                adaylar = [ana_cumle(m) for _, m in kodlar[kod] if re.match(f"[{BUYUK}]", m.strip())]
                adaylar = [a.split(". ")[0].rstrip(".") + "." for a in adaylar]
            if adaylar:
                print(f"- **{kod}** — {adaylar[0]}")
            else:
                yalniz_kod.append(kod)
        if yalniz_kod:
            print("- Korpusta yalnız açıklama metni içinde geçenler (tam ifade için `kazanim_ara`): "
                  + ", ".join(yalniz_kod))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in DERSLER:
        sys.exit("kullanım: skill_unite_haritasi.py " + "|".join(DERSLER))
    main(sys.argv[1])
