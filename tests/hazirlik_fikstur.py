"""Sınav hazırlığı testlerinin ortak fikstürleri (plan Görev 6–8): gerçek senaryo tablosu, Fen 7-1'den ölçülmüş
değerlerle kurulmuş küçük bir harita (gerçek dosyadan bağımsız) ve /api/exams biçiminde sınav kayıtları."""
from __future__ import annotations

from datetime import date

from src import sinav_kilavuzu as sk
from src.sinav_senaryo import tablo_oku

TABLO = tablo_oku()
BUGUN = date(2026, 10, 25)
PDF = "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf"
DUYURU = "Sınav, İstanbul İl MEB tarafından belirlenen 2. senaryoya göre uygulanacaktır."
FEN_KONULARI = ("Uzay teknolojileri", "Uzay araştırmalarının sorunları", "Fiziksel anlamda iş")


def _b(tur, ad, sayfa, amac=None):
    return {"ad": ad, "tur": tur, "amac": amac, "sayfa": sayfa}


def _k(ad, sayfa, son, *basliklar):
    return {"ad": ad, "sayfa": sayfa, "son_sayfa": son, "basliklar": list(basliklar)}


def _c(no, ad, sayfa, son, ciktilar, konular, basliklar=()):
    return {"no": no, "ad": ad, "sayfa": sayfa, "son_sayfa": son, "ciktilar": list(ciktilar),
            "basliklar": list(basliklar), "konular": list(konular)}


def fen_haritasi() -> dict:
    uniteler = [
        {"no": 1, "ad": "Uzay Çağı", "sayfa": 14, "son_sayfa": 57, "cerceveler": [
            _c(1, "Türkiye ve Uzay Araştırmaları", 15, 33, ["FB.7.1.1", "FB.7.1.2", "FB.7.1.3"], [
                _k("Uzay Teknolojileri", 16, 24, _b("etkinlik", "Keşif Noktası: Uzay Teknolojileri", 17),
                   _b("kontrol", "Kontrol Noktası", 19), _b("diger", "Teleskop Çeşitleri", 22),
                   _b("kontrol", "Kontrol Noktası", 24)),
                _k("Teknoloji ile Uzay Araştırmaları Arasındaki İlişki", 24, 33, _b("baglanti", "Bağlantı Noktası", 25),
                   _b("tanim", "Astronot", 26),
                   _b("etkinlik", "Performans Görevi: Uzay Gözlem Araçları Modeli", 29,
                      "Uzay gözlem araçları ile ilgili bilimsel model oluşturma"),
                   _b("ozet", "Neler Öğrendik?", 33))],
               [_b("baglanti", "Bağlantı Noktası", 15)]),
            _c(2, "Uzayda Neler Var?", 34, 49, ["FB.7.1.4", "FB.7.1.5"], [
                _k("Yıldız Oluşumu", 35, 49,
                   _b("etkinlik", "Etkinlik Noktası-1", 36,
                      "Yıldızların yaşam sürecine ilişkin kavramlar arasındaki ilişkileri açıklama"),
                   _b("diger", "Galaksiler", 48), _b("ozet", "Neler Öğrendik?", 49))],
               [_b("baglanti", "Bağlantı Noktası", 34)])]},
        {"no": 2, "ad": "Kuvvet ve Enerjiyi Keşfedelim", "sayfa": 58, "son_sayfa": 87, "cerceveler": [
            _c(1, "Kuvvet, İş ve Enerji İlişkisi", 59, 70, ["FB.7.2.1", "FB.7.2.2"], [
                _k("Fiziksel Anlamda İş", 60, 63,
                   _b("etkinlik", "Etkinlik Noktası-1", 60, "Fiziksel anlamda yapılan işin niteliklerini tanımlama"),
                   _b("etkinlik", "Etkinlik Noktası-2", 60,
                      "Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme"),
                   _b("baglanti", "Bağlantı Noktası", 62), _b("kontrol", "Kontrol Noktası", 63)),
                _k("Enerji ve Enerji Çeşitleri", 64, 70,
                   _b("etkinlik", "Etkinlik Noktası-3", 65, "Kinetik ve potansiyel enerjiyi karşılaştırma"),
                   _b("tanim", "Potansiyel Enerji", 68), _b("ozet", "Neler Öğrendik?", 70))],
               [_b("baglanti", "Bağlantı Noktası", 59)]),
            _c(2, "Enerji Dönüşümleri", 71, 79, ["FB.7.2.3"], [
                _k("Enerjinin Korunumu", 72, 79, _b("ozet", "Neler Öğrendik?", 78))])]},
        {"no": 3, "ad": "Vücudumuzdaki Sistemler", "sayfa": 88, "son_sayfa": 148, "cerceveler": [
            _c(1, "Sindirim Sistemi", 89, 100, ["FB.7.3.1", "FB.7.3.2"], [
                _k("Sindirim Sistemini Oluşturan Yapı ve Organlar", 90, 95, _b("kontrol", "Kontrol Noktası", 93)),
                _k("Sindirim Sisteminin Sağlığı", 96, 100, _b("ozet", "Neler Öğrendik?", 100))]),
            _c(2, "Dolaşım Sistemi", 101, 116, ["FB.7.3.3", "FB.7.3.4", "FB.7.3.5"], [
                _k("Dolaşım Sistemini Oluşturan Yapı ve Organlar", 102, 109, _b("diger", "Kanın Yapısı ve Görevleri", 107)),
                _k("Kan Bağışının Toplum Açısından Önemi", 109, 112, _b("baglanti", "Bağlantı Noktası", 112)),
                _k("Dolaşım Sisteminin Sağlığı", 113, 116, _b("ozet", "Neler Öğrendik?", 116))]),
            _c(3, "Solunum Sistemi", 117, 128, ["FB.7.3.6"], [
                _k("Solunum Sistemini Oluşturan Yapı ve Organlar", 118, 122, _b("baglanti", "Bağlantı Noktası", 122)),
                _k("Solunum Sisteminin Sağlığı", 123, 128, _b("ozet", "Neler Öğrendik?", 128))])]},
    ]

    def e(u, c, konu):
        return {"kitap": 0, "unite": u, "cerceve": c, "konu": konu}
    teknoloji = "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"
    eslesme = {
        "FB.7.1.1": [e(1, 1, "Uzay Teknolojileri"), e(1, 1, teknoloji)],
        "FB.7.1.2": [e(1, 1, "Uzay Teknolojileri"), e(1, 1, teknoloji)],
        "FB.7.1.3": [e(1, 1, teknoloji)],
        "FB.7.1.4": [e(1, 2, "Yıldız Oluşumu")], "FB.7.1.5": [e(1, 2, "Yıldız Oluşumu")],
        "FB.7.2.1": [e(2, 1, "Fiziksel Anlamda İş")], "FB.7.2.2": [e(2, 1, "Enerji ve Enerji Çeşitleri")],
        "FB.7.2.3": [e(2, 2, "Enerjinin Korunumu")],
        "FB.7.3.1": [e(3, 1, "Sindirim Sistemini Oluşturan Yapı ve Organlar")],
        "FB.7.3.2": [e(3, 1, "Sindirim Sisteminin Sağlığı")],
        "FB.7.3.3": [e(3, 2, "Dolaşım Sistemini Oluşturan Yapı ve Organlar")],
        "FB.7.3.4": [e(3, 2, "Kan Bağışının Toplum Açısından Önemi")],
        "FB.7.3.5": [e(3, 2, "Dolaşım Sisteminin Sağlığı")],
        "FB.7.3.6": [e(3, 3, "Solunum Sistemini Oluşturan Yapı ve Organlar")]}
    return {"surum": 1, "ders": "Fen Bilimleri", "anahtar": "fen-bilimleri", "uretildi": "2026-10-25",
            "senaryo_tablosu": {"meb_guncelleme": "2026-09-10T17:27",
                                "ders_sha256": TABLO["dersler"]["Fen Bilimleri"]["sha256"]},
            "kitaplar": [{"baslik": "Fen Bilimleri 7 (1. Kitap)", "pdf_url": PDF, "kaynak_sayfa": None, "sha256": "a" * 64,
                          "baski": "2026-2027", "sayfa_kaymasi": 1, "toplam_sayfa": 153, "uniteler": uniteler}],
            "eslesme": eslesme, "eslesmedi": [], "denetim": {"kim": "test", "tarih": "2026-10-25"}}


def sinav_kaydi(ders="Fen Bilimleri", no=1, *, durum="dogrulandi", senaryo=2, tarih="2026-11-03", status="upcoming",
                konular=(), anilan=None, sid="fen11", eslesmeyen=(), senaryo_disi=(),
                duyuruda=("FB.7.1.1", "FB.7.1.3", "FB.7.2.1")) -> dict:
    """/api/exams kaydının hazırlık modelinin okuduğu alanları; senaryo bloğu sinav_senaryo.senaryo_blogu biçiminde."""
    dt = TABLO["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    kesin = durum in sk.KESIN_DURUMLAR
    dagilim = []
    if kesin and senaryo:
        d = sinav["senaryolar"][str(senaryo)]
        dagilim = [{"kod": c["kod"], "metin": c["metin"], "soru": d[c["kod"]], "duyuruda": c["kod"] in duyuruda}
                   for c in dt["ciktilar"] if c["kod"] in d]
    blok = {"durum": durum, "ders": ders, "sinav_no": no, "donem": 1,
            "anilan": list(anilan if anilan is not None else ([senaryo] if senaryo else [])),
            "cumle": DUYURU if senaryo else None, "senaryo": senaryo if kesin else None,
            "toplam": sum(x["soru"] for x in dagilim) if dagilim else None, "dagilim": dagilim,
            "eslesen_konu_sayisi": len(konular) - len(eslesmeyen), "eslesmeyen_konular": list(eslesmeyen),
            "senaryo_disi_konular": list(senaryo_disi), "adaylar": [], "senaryo_sayisi": len(sinav.get("senaryolar", {})),
            "kaynak": TABLO["kaynak"]["sayfa"], "meb_guncelleme": TABLO["kaynak"]["meb_guncelleme"]}
    return {"id": sid, "course": ders, "title": f"{ders} {no}. Yazılı", "date": tarih, "status": status,
            "konular": list(konular), "senaryo": blok}


def girdiler(**degisiklik) -> sk.Girdiler:
    taban = {"tablo": TABLO, "haritalar": {"fen-bilimleri": fen_haritasi()},
             "sinavlar": [sinav_kaydi(konular=FEN_KONULARI)], "bugun": BUGUN}
    taban.update(degisiklik)
    return sk.Girdiler(**taban)
