"""Live, structured student-data tools for the assistant (plan Görev 2).

Audit 2026-09-25 (docs/superpowers/notes/2026-09-25-asistan-veri-denetimi.md
§2a, §3): the assistant could not reach /api/schedule, /api/calendar/unified,
/api/content or /api/content/weeks at all, saw exams only through takvim
titles and grades without rubrics — and `_fmt_scraped_data` expected shapes
the scraper stopped writing long ago, so the weekly timetable and the course
content text never reached the BM25 index either. "ders programı yarın"
returned eight sync.log chunks.

Every fixture below has the real shape of output/scraped_data.json and
invented values: no real names, teachers, e-mails, ids or grades.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import assistant_tools as at  # noqa: E402
from src.assistant_tools import build_registry  # noqa: E402

GOVDE_SINIRI = 3900

# ── Fixtures: real shapes, invented values ──────────────────────────────────

# The portal's grid: headers empty, day names in rows[0] in caps (dotless I),
# two blocks side by side — Mon–Thu and Fri–Sun — each with its own time
# column under a blank header, because Friday runs on a later bell. Break rows
# are short (five cells) and do not line up with the day columns.
BASLIK = ["", "PAZARTESI", "SALI", "ÇARŞAMBA", "PERŞEMBE", "", "CUMA", "CUMARTESI", "PAZAR"]
SATIRLAR = [
    BASLIK,
    ["1. Ders\n\n08:00 - 08:40",
     "Türkçe (i-901 (Türkçe))\nDeneme Öğretmen",
     "Matematik (i-902 (Matematik))\nÖrnek Hoca",
     "Fen Bilimleri (i-903 (Fen Bilimleri))\nKurgu Öğretmen",
     "Matematik (i-902 (Matematik))\nÖrnek Hoca",
     "1. Ders\n\n08:00 - 08:40",
     "Sosyal Bilgiler (i-904 (Sosyal Bilgiler))\nHayali Öğretmen",
     "", ""],
    ["08:40 - 08:55", "Kahvaltı", "08:40 - 09:00", "Kahvaltı", ""],
    ["2. Ders\n\n08:55 - 09:35",
     "İkinci Yabancı Dil (Fransızca) (i-905)\nUydurma Hoca",
     "Görsel Sanatlar (i-906 (Görsel Sanatlar))\nTemsili Öğretmen",
     "İngilizce (Language) (i-907 (İngilizce))\nÖrnek Teacher",
     "Beden Eğitimi ve Spor (Spor Salonu)\nDeneme Koç",
     "2. Ders\n\n09:00 - 09:40",
     "Fen Bilimleri (i-903 (Fen Bilimleri))\nKurgu Öğretmen",
     "", ""],
    ["3. Ders\n\n09:45 - 10:25",
     "Müzik (i-908)\nHayali Müzisyen",
     "",
     "Türkçe (i-901 (Türkçe))\nDeneme Öğretmen",
     "Din Kültürü ve Ahlak Bilgisi (i-909 (DKAB))\nTemsili Hoca",
     "3. Ders\n\n09:50 - 10:30",
     "Matematik (i-902 (Matematik))\nÖrnek Hoca",
     "", ""],
    ["12:00 - 12:40", "Öğle yemeği", "12:10 - 12:50", "Öğle yemeği", ""],
    ["15:45", "Çıkış", "13:30", "Çıkış", ""],
]
HAFTA = {
    "week_label": "2. Hafta 21 Eyl. - 27 Eyl.",
    "week_index": 1,
    "is_current": True,
    "schedule": {"headers": [], "rows": SATIRLAR, "empty_state": False},
    "screenshot": "",
}

UTC = timezone.utc


def _kopya(x):
    return json.loads(json.dumps(x))


# ── 1. Ders programı: two blocks, Friday's own bell ─────────────────────────

def test_gun_sutunlari_noktasiz_buyuk_harfle_eslesir():
    # utils/schedule.ts normDay: the portal writes "PAZARTESI" with a dotless
    # I; Monday — the one day with an i — silently failed to match before.
    cols = at.gun_sutunlari(BASLIK, ["Pazartesi", "Cuma", "Pazar"])
    assert [(g, i, t) for g, i, t in cols] == [("Pazartesi", 1, 0), ("Cuma", 6, 5), ("Pazar", 8, 5)]


def test_iki_bloklu_tabloda_cuma_kendi_zilini_okur():
    cuma = at.gunun_dersleri(SATIRLAR, "Cuma")
    assert [(d["ders_no"], d["baslangic"], d["bitis"], d["ders"]) for d in cuma] == [
        (1, "08:00", "08:40", "Sosyal Bilgiler"),
        (2, "09:00", "09:40", "Fen Bilimleri"),
        (3, "09:50", "10:30", "Matematik"),
    ]
    pazartesi = at.gunun_dersleri(SATIRLAR, "Pazartesi")
    # Monday's second lesson is on the early bell, and its name is normalised.
    assert (pazartesi[1]["baslangic"], pazartesi[1]["ders"]) == ("08:55", "Fransızca")
    # Break rows ("Kahvaltı", "Öğle yemeği") are not lessons.
    assert all(d["ders"] not in ("Kahvaltı", "Öğle yemeği") for d in pazartesi)


def test_yarin_istanbul_tarihine_gore_cozulur():
    # 23.09 22:30 UTC is already Thursday 24.09 01:30 in Istanbul; "yarın" is
    # Friday. Read on the host's UTC clock it would be Thursday.
    reg = build_registry(lambda q, k: [], program_kaynagi=lambda: _kopya(HAFTA),
                         saat=lambda: datetime(2026, 9, 23, 22, 30, tzinfo=UTC))
    out = reg.dispatch(at.PROGRAM_TOOL, {"gun": "yarın"})
    assert out.ok, out.error
    assert "Cuma 25.09.2026" in out.text
    assert "09:00–09:40 Fen Bilimleri" in out.text        # Friday's bell, not 08:55
    assert "Din Kültürü" not in out.text                   # Thursday's lesson
    assert out.text.startswith("Bugün: Perşembe 24.09.2026 01:30")


def test_istanbul_simdi_saf_saati_oldugu_gibi_birakir():
    assert at.istanbul_simdi(datetime(2026, 9, 24, 10, 0)) == datetime(2026, 9, 24, 10, 0)
    assert at.istanbul_simdi(datetime(2026, 9, 24, 7, 0, tzinfo=UTC)) == datetime(2026, 9, 24, 10, 0)


def test_hafta_sonu_okul_yok_der_ve_sonraki_okul_gununu_verir():
    cumartesi = datetime(2026, 9, 26, 11, 0)
    metin = at.ders_programi_metni(HAFTA, "bugün", cumartesi)
    assert "Cumartesi 26.09.2026" in metin and "okul yok" in metin
    assert "Pazartesi 28.09.2026" in metin and "08:00–08:40 Türkçe" in metin
    assert "okul yok" in at.ders_programi_metni(HAFTA, "Pazar", cumartesi)


def test_gun_adi_buyuk_kucuk_ve_aksansiz_verilebilir():
    simdi = datetime(2026, 9, 24, 16, 10)
    for gun in ("perşembe", "PERSEMBE", "Persembe"):
        assert "Din Kültürü" in at.ders_programi_metni(HAFTA, gun, simdi)


def test_gun_verilmezse_butun_hafta():
    metin = at.ders_programi_metni(HAFTA, None, datetime(2026, 9, 24, 16, 10))
    for gun in ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"):
        assert gun in metin
    assert "2. Hafta 21 Eyl. - 27 Eyl." in metin
    assert "Deneme Öğretmen" not in metin     # teachers stay out of the body


def test_bugun_biten_ders_isaretlenir():
    metin = at.ders_programi_metni(HAFTA, "bugün", datetime(2026, 9, 24, 9, 0))
    assert "08:00–08:40 Matematik (bitti)" in metin
    assert "08:55–09:35 Beden Eğitimi (şu an)" in metin


def test_bilinmeyen_gun_modele_hata_doner():
    reg = build_registry(lambda q, k: [], program_kaynagi=lambda: _kopya(HAFTA))
    out = reg.dispatch(at.PROGRAM_TOOL, {"gun": "gelecek ay"})
    assert not out.ok and "gün" in out.error


def test_program_yoksa_bunu_soyler():
    metin = at.ders_programi_metni({}, None, datetime(2026, 9, 24, 16, 10))
    assert "ders programı yok" in metin.lower()


def test_program_araci_okur_adiyla_atif_verir():
    reg = build_registry(lambda q, k: [], program_kaynagi=lambda: _kopya(HAFTA))
    out = reg.dispatch(at.PROGRAM_TOOL, {})
    atif = out.citations[0]
    assert atif["kind"] == "ogrenci" and atif["label"] == "Ders programı"


# ── 2. Sınavlar: the same list /api/exams serves ────────────────────────────

def _portal(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "+03:00"


def _etkinlik(baslik, start, end="", aciklama=None, yer=""):
    return {"title": baslik, "start": start, "end": end, "allDay": False,
            "backgroundColor": "", "extendedProps": {"description": aciklama, "location": yer,
                                                     "calendar": "diger"}}


def _sinav_verisi():
    simdi = datetime.now()
    return {
        "takvim": [
            _etkinlik("7. Sınıf MEB Ülke Geneli Türkçe 1. Dönem 2. Ortak Yazılı Sınavı",
                      _portal(simdi + timedelta(days=10)), _portal(simdi + timedelta(days=10, hours=1))),
            _etkinlik("5-6-7. Sınıflar Deneme Gelişim İzleme Sınavı GİS-1 (Türkiye Geneli)",
                      _portal(simdi + timedelta(days=3))),
            _etkinlik("7. Sınıflar Matematik 1. Yazılı Sınavı",
                      _portal(simdi - timedelta(days=20))),
            _etkinlik("Kulüp Tanıtımları", _portal(simdi + timedelta(days=1))),
        ],
        "odevlerim": {"summary": "", "homework": {"rows": []}},
        "gelisim_raporu": {"semester": "2026-2027 1. Dönem",
                           "grades": [{"Ders": "Fen Bilimleri", "1. Sınav": "77", "2. Sınav": "-",
                                       "3. Sınav": "-", "DİKP/Performans-1": "-",
                                       "DİKP/Performans-2": "-", "DİKP/Performans-3": "-"}],
                           "rubrics": []},
        "ders_icerikleri": {},
    }


@pytest.fixture
def api(monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [])
    api.app.config["TESTING"] = True
    return api


def test_sinavlar_api_exams_ile_ayni_listeyi_verir(api, monkeypatch):
    veri = _sinav_verisi()
    monkeypatch.setattr(api, "_scraped", lambda: _kopya(veri))
    with api.app.test_client() as c:
        rota = c.get("/api/exams").get_json()["exams"]
    canli = api._canli_sinavlar()
    assert [e["id"] for e in canli] == [e["id"] for e in rota]
    assert [e["status"] for e in canli] == [e["status"] for e in rota]

    reg = build_registry(lambda q, k: [], sinav_kaynagi=api._canli_sinavlar)
    out = reg.dispatch(at.SINAV_TOOL, {})
    assert out.ok, out.error
    yaklasan = out.text[out.text.index("YAKLAŞAN"):out.text.index("GEÇMİŞ")]
    gecmis = out.text[out.text.index("GEÇMİŞ"):]
    for e in rota:
        hedef = yaklasan if e["status"] == "upcoming" else gecmis
        assert e["course"] in hedef
    assert "Kulüp Tanıtımları" not in out.text          # not an exam
    assert "not 77" in gecmis                             # the synthetic, graded one
    assert out.citations[0]["label"] == "Sınavlar"


def test_sinavlar_metni_tarih_ve_turu_yazar():
    simdi = datetime(2026, 9, 24, 16, 10)
    sinavlar = [
        {"id": "a", "course": "Türkçe", "title": "Türkçe · 1. Dönem 2. Yazılı",
         "rawTitle": "7. Sınıf Türkçe 1. Dönem 2. Yazılı", "date": "2026-10-05T10:30:00",
         "allDay": False, "status": "upcoming", "grade": None, "examNumber": 2},
        {"id": "b", "course": "Matematik", "title": "Matematik · 1. Yazılı",
         "rawTitle": "Matematik 1. Sınav", "date": None, "allDay": False,
         "status": "past", "grade": "64", "examNumber": 1},
    ]
    metin = at.sinavlar_metni(sinavlar, simdi)
    assert "Türkçe — 1. Dönem 2. Yazılı · Pazartesi 05.10.2026 10:30 (11 gün sonra)" in metin
    assert "Matematik — 1. Yazılı · tarihi yok · not 64" in metin


def test_sinav_yoksa_bunu_soyler():
    assert "sınav yok" in at.sinavlar_metni([], datetime(2026, 9, 24)).lower()


# ── 3. Takvim: the unified events, today onwards ────────────────────────────

def test_takvim_pencereyi_ve_turleri_suzer():
    simdi = datetime(2026, 9, 24, 16, 10)
    etkinlikler = [
        {"id": "1", "type": "event", "title": "Kulüp Tanıtımları", "start": "2026-09-24T12:40:00",
         "end": "2026-09-24T14:10:00", "description": "<p>Kulüp Tanıtımları</p>"},
        {"id": "2", "type": "event", "title": "Deprem Tatbikatı", "start": "2026-10-05T10:00:00",
         "end": "2026-10-05T11:00:00", "description": "<p>Tören&nbsp;bahçede yapılacak.</p><p>Held outside.</p>",
         "location": "Bahçe"},
        {"id": "3", "type": "event", "title": "Uzak Gezi", "start": "2026-11-20T08:00:00",
         "end": "2026-11-20T15:00:00"},
        {"id": "4", "type": "event", "title": "Fotoğraf Çekimi Haftası", "start": "2026-09-21T07:45:00",
         "end": "2026-09-25T16:30:00"},
        {"id": "5", "type": "private_lesson", "title": "Matematik · Deneme Hoca",
         "start": "2026-09-28T17:00:00", "end": "2026-09-28T18:00:00", "course": "Matematik"},
        {"id": "6", "type": "sebit", "title": "Kesirler Çalışması", "course": "Matematik",
         "start": "2026-09-20T09:00:00", "end": "2026-09-30T23:00:00", "status": "Devam Ediyor"},
        {"id": "7", "type": "sebit", "title": "Geçen Yılın Çalışması", "course": "Fen Bilimleri",
         "start": "2026-05-18T06:57:00", "end": "2026-06-07T06:52:00", "status": "Süresi Doldu"},
        {"id": "8", "type": "lesson", "title": "Türkçe", "start": "2026-09-25T08:00:00",
         "end": "2026-09-25T08:40:00"},
        {"id": "9", "type": "homework", "title": "Test 2", "start": "2026-09-26T12:00:00",
         "end": "2026-09-26T12:00:00"},
        {"id": "10", "type": "ogep", "title": "ÖGEP Okuma", "start": "2026-09-29T15:00:00",
         "end": "2026-09-29T16:00:00", "status": "Bekliyor"},
    ]
    metin = at.takvim_metni(etkinlikler, simdi, 14)
    for beklenen in ("Kulüp Tanıtımları", "Deprem Tatbikatı", "Fotoğraf Çekimi Haftası",
                     "Matematik · Deneme Hoca", "Kesirler Çalışması", "ÖGEP Okuma"):
        assert beklenen in metin, beklenen
    for yok in ("Uzak Gezi", "Geçen Yılın Çalışması", "Test 2", "08:00–08:40 Türkçe"):
        assert yok not in metin, yok
    # htmlToText equivalent; a description that only repeats the title is dropped.
    assert "Tören bahçede yapılacak. Held outside." in metin and "<p>" not in metin
    assert metin.count("Kulüp Tanıtımları") == 1
    assert "Bahçe" in metin
    assert metin.index("Fotoğraf Çekimi") < metin.index("Kulüp") < metin.index("Deprem")


def test_takvim_gun_sayisi_daraltir():
    simdi = datetime(2026, 9, 24, 16, 10)
    ev = [{"id": "2", "type": "event", "title": "Deprem Tatbikatı",
           "start": "2026-10-05T10:00:00", "end": "2026-10-05T11:00:00"}]
    assert "Deprem" not in at.takvim_metni(ev, simdi, 3)
    assert "takvimde bir şey yok" in at.takvim_metni(ev, simdi, 3)


def test_canli_takvim_birlesik_rotanin_etkinliklerini_aciklamayla_verir(api, monkeypatch):
    simdi = datetime.now()
    veri = _sinav_verisi()
    veri["takvim"].append(_etkinlik("Veli Semineri", _portal(simdi + timedelta(days=2)),
                                     aciklama="<p>Seminer çevrim içi yapılacak.</p>", yer="Teams"))
    monkeypatch.setattr(api, "_scraped", lambda: _kopya(veri))
    ders = {"id": "pl1", "course": "Matematik", "teacher": "Deneme Hoca", "is_recurring": True,
            "weekday": "Pazartesi", "date": "", "start_time": "17:00", "end_time": "18:00",
            "active": True}
    cumartesi = dict(ders, id="pl2", course="Fen Bilimleri", weekday="Cumartesi",
                     start_time="12:00", end_time="13:00")
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [ders, cumartesi])
    with api.app.test_client() as c:
        rota = c.get("/api/calendar/unified").get_json()["events"]
    canli = api._canli_takvim()
    # Measured 2026-09-25: both real private lessons are on Saturday, which
    # the Mon–Fri week grid never draws; the assistant must still see them.
    assert not any(e.get("course") == "Fen Bilimleri" for e in rota if e["type"] == "private_lesson")
    assert any(e.get("course") == "Fen Bilimleri" for e in canli if e["type"] == "private_lesson")
    rota_etkinlik = {e["id"] for e in rota if e["type"] == "event"}
    assert rota_etkinlik == {e["id"] for e in canli if e["type"] == "event"}
    # The route's shape is unchanged; the assistant's copy carries the text.
    assert all("description" not in e for e in rota)
    seminer = next(e for e in canli if e["title"] == "Veli Semineri")
    assert seminer["description"] == "<p>Seminer çevrim içi yapılacak.</p>" and seminer["location"] == "Teams"
    # Private lessons beyond this week, which the week-bound route cannot draw.
    ozel = sorted(e["start"] for e in canli if e["type"] == "private_lesson")
    assert len(ozel) >= 3 and len(set(ozel)) == len(ozel)

    reg = build_registry(lambda q, k: [], takvim_kaynagi=api._canli_takvim)
    out = reg.dispatch(at.TAKVIM_TOOL, {"gun_sayisi": 14})
    assert out.ok, out.error
    assert "Veli Semineri" in out.text and "Seminer çevrim içi yapılacak." in out.text
    assert "Matematik · Deneme Hoca" in out.text
    assert out.citations[0]["label"] == "Takvim"


# ── 4. Ders içeriği: a chosen week, names through normalize_course ──────────

def _icerik(metin, maddeler=(), kartlar=()):
    return {"tab_id": 6, "text": metin, "tables": [], "items": list(maddeler), "cards": list(kartlar)}


HATA = {"tab_id": "tab_x", "error": "Message: no such element: Unable to locate element\nStacktrace:\n#0 0xdead"}

HAFTALAR = {
    "1. Hafta 14 Eyl. - 20 Eyl.": {
        "Matematik": _icerik("1. HAFTA MATEMATİK: DOĞAL SAYILAR\nDeneme Öğretmen | 14.09.2026\nBu hafta doğal sayıları tekrar ediyoruz."),
        "Genel": _icerik("Okulumuzda yeni dönem\nOkul Yönetimi | 14.09.2026\n  1 Yorum yapıldı!\n  Daha fazla oku\nUydurma Öğrenci Adı\n3\nçok güzel\nYorum Ekle"),
    },
    "2. Hafta 21 Eyl. - 27 Eyl.": {
        "Matematik": _icerik("2. HAFTA MATEMATİK: TAM SAYILAR\nDeneme Öğretmen | 21.09.2026\nSayı doğrusunda tam sayıları inceleyeceğiz.\n  İlk yorum yapan sen olmak ister misin?\n  Daha fazla oku\nYorum Ekle",
                             maddeler=["Mutlak değeri keşfedeceğiz,"]),
        "Fen Bilimleri": _icerik("2. HAFTA FEN: GÜNEŞ SİSTEMİ\nKurgu Öğretmen | 21.09.2026\nGezegenlerin yörüngelerini modelleyeceğiz."),
        "DKAB": _icerik("Din Kültürü haftalık plan: ahlaki değerler."),
        "İngilizce Language": _icerik("Unit 2: Daily routines."),
        "İngilizce (2)": _icerik("Reading: a short story about a lighthouse."),
        "Müzik": _icerik(""),
    },
    "3. Hafta 28 Eyl. - 04 Eki.": {
        "Matematik": _icerik("3. HAFTA MATEMATİK: RASYONEL SAYILAR\nDeneme Öğretmen | 28.09.2026\nRasyonel sayıları sayı doğrusunda göstereceğiz.",
                             kartlar=["3. HAFTA MATEMATİK: RASYONEL SAYILAR\nDeneme Öğretmen | 28.09.2026\nRasyonel sayıları sayı doğrusunda göstereceğiz.",
                                      "Ek etkinlik: kesir kartları oyunu"]),
    },
}
GUNCEL = {
    # The open week as scraped this run: one course read, one that failed.
    "Matematik": _icerik("2. HAFTA MATEMATİK: TAM SAYILAR (güncel okuma)\nSayı doğrusunda tam sayıları inceleyeceğiz.",
                         maddeler=["Mutlak değeri keşfedeceğiz,"]),
    "Fen Bilimleri": HATA,
}
ICERIK = {"guncel": GUNCEL, "haftalar": HAFTALAR, "guncel_hafta": "2. Hafta 21 Eyl. - 27 Eyl."}


def test_ders_icerigi_belirli_haftayi_dondurur():
    reg = build_registry(lambda q, k: [], icerik_kaynagi=lambda: _kopya(ICERIK))
    out = reg.dispatch(at.ICERIK_TOOL, {"ders": "Matematik", "hafta": 3})
    assert out.ok, out.error
    assert "RASYONEL SAYILAR" in out.text and "TAM SAYILAR" not in out.text
    assert "Ek etkinlik: kesir kartları oyunu" in out.text           # a card not already in text
    assert out.text.count("Rasyonel sayıları sayı doğrusunda göstereceğiz.") == 1
    assert out.citations[0]["label"] == "Matematik · 3. hafta içeriği"


def test_guncel_hafta_ders_icerikleri_nden_gelir_okunamazsa_haftalardan():
    metin, etiket = at.ders_icerigi_metni(_kopya(ICERIK), "Matematik", None)
    assert "(güncel okuma)" in metin and etiket == "Matematik · 2. hafta içeriği"
    metin, _ = at.ders_icerigi_metni(_kopya(ICERIK), "Fen Bilimleri", None)
    assert "GÜNEŞ SİSTEMİ" in metin
    assert "Stacktrace" not in metin and "no such element" not in metin


def test_ders_adi_normalize_course_ile_eslesir_ve_varyantlar_birlesir():
    metin, etiket = at.ders_icerigi_metni(_kopya(ICERIK), "Din Kültürü", 2)
    assert "ahlaki değerler" in metin and etiket == "Din Kültürü · 2. hafta içeriği"
    metin, _ = at.ders_icerigi_metni(_kopya(ICERIK), "ingilizce", 2)
    assert "Daily routines" in metin and "lighthouse" in metin
    metin, etiket = at.ders_icerigi_metni(_kopya(ICERIK), "mat", 2)
    assert "TAM SAYILAR" in metin and etiket.startswith("Matematik")


def test_ders_verilmezse_guncel_haftanin_dersleri_listelenir():
    metin, etiket = at.ders_icerigi_metni(_kopya(ICERIK), None, None)
    for ders in ("Matematik", "Fen Bilimleri", "Din Kültürü", "İngilizce"):
        assert ders in metin
    assert "Müzik" in metin and "içerik yok" in metin
    assert etiket == "Ders içerikleri · 2. hafta"


def test_bilinmeyen_hafta_ve_ders_bunu_soyler():
    metin, _ = at.ders_icerigi_metni(_kopya(ICERIK), "Matematik", 30)
    assert "30. hafta" in metin and "1, 2, 3" in metin
    metin, _ = at.ders_icerigi_metni(_kopya(ICERIK), "Astronomi", 2)
    assert "Astronomi" in metin and "Matematik" in metin


def test_yorum_blogu_ve_portal_susu_atilir():
    ozet = at.icerik_ozeti(HAFTALAR["1. Hafta 14 Eyl. - 20 Eyl."]["Genel"])
    assert "Okulumuzda yeni dönem" in ozet
    # Other children's names and comments sit between "Daha fazla oku" and
    # "Yorum Ekle"; the portal's buttons are chrome.
    for yok in ("Uydurma Öğrenci Adı", "çok güzel", "Daha fazla oku", "Yorum Ekle", "Yorum yapıldı"):
        assert yok not in ozet


# ── 5. Notlar: grades, rubrics, the term's name; last year labelled ─────────

GELISIM = {
    "semester": "2025-2026 4. Arakarne",
    "grades": [
        {"Ders": "Matematik", "1. Sınav": "71", "2. Sınav": "83", "3. Sınav": "-",
         "DİKP/Performans-1": "90", "DİKP/Performans-2": "-", "DİKP/Performans-3": "-"},
        {"Ders": "Fen Bilimleri", "1. Sınav": "-", "2. Sınav": "-", "3. Sınav": "-",
         "DİKP/Performans-1": "-", "DİKP/Performans-2": "-", "DİKP/Performans-3": "-"},
    ],
    "physical": {},
    "rubrics": [
        {"ders": "Beden Eğitimi ve Spor", "alan": "HAREKET", "kazanim": "Denge becerilerini sergiler.",
         "duzey": "Kazanımın Üstünde"},
        {"ders": "Beden Eğitimi ve Spor", "alan": "HAREKET", "kazanim": "Top sürme becerisini geliştirir.",
         "duzey": "Kazanımda"},
        {"ders": "Müzik", "alan": "DİNLEME", "kazanim": "Ritim kalıplarını ayırt eder.",
         "duzey": "Kazanımda"},
    ],
}


def test_notlar_eski_yili_acikca_etiketler():
    reg = build_registry(lambda q, k: [], not_kaynagi=lambda: {"gelisim": _kopya(GELISIM),
                                                                "ogretim_yili": "2026-2027"})
    out = reg.dispatch(at.NOT_TOOL, {})
    assert out.ok, out.error
    assert "ÖNCEKİ ÖĞRETİM YILI" in out.text and "2025-2026 4. Arakarne" in out.text
    assert "Matematik · 1. Sınav 71 · 2. Sınav 83 · DİKP/Performans-1 90" in out.text
    assert "Fen Bilimleri ·" not in out.text                    # nothing entered
    assert "Denge becerilerini sergiler. → Kazanımın Üstünde" in out.text
    assert "Beden Eğitimi ve Spor: Kazanımda 1, Kazanımın Üstünde 1" in out.text
    assert out.citations[0]["label"] == "Notlar · 2025-2026 4. Arakarne"


def test_notlar_bu_yilinsa_eski_demez():
    g = dict(_kopya(GELISIM), semester="2026-2027 1. Arakarne")
    metin, _ = at.notlar_metni({"gelisim": g, "ogretim_yili": "2026-2027"})
    assert "ÖNCEKİ" not in metin


def test_not_yoksa_bunu_soyler():
    metin, etiket = at.notlar_metni({"gelisim": {"semester": "", "grades": [], "rubrics": []},
                                     "ogretim_yili": "2026-2027"})
    assert "henüz not" in metin and etiket == "Notlar"


# ── 6. Registry: declared only with a source; failures reach the model ─────

# Literal names: the model sees these, so a rename is a contract change.
YENI_ARACLAR = ("ders_programi", "sinavlar", "takvim", "ders_icerigi", "notlar")


def _tam_kayit():
    return build_registry(
        lambda q, k: [],
        program_kaynagi=lambda: _kopya(HAFTA), sinav_kaynagi=lambda: [],
        takvim_kaynagi=lambda: [], icerik_kaynagi=lambda: _kopya(ICERIK),
        not_kaynagi=lambda: {"gelisim": _kopya(GELISIM), "ogretim_yili": "2026-2027"})


def test_araclar_yalniz_kaynak_verilince_ilan_edilir():
    adlar = {d["name"] for d in build_registry(lambda q, k: []).declarations()}
    assert not adlar & set(YENI_ARACLAR)
    adlar = {d["name"] for d in _tam_kayit().declarations()}
    assert set(YENI_ARACLAR) <= adlar
    for arac in YENI_ARACLAR:
        out = build_registry(lambda q, k: []).dispatch(arac, {})
        assert not out.ok and "bilinmeyen araç" in out.error


def test_kaynak_patlarsa_modele_hata_gider():
    def patlak():
        raise OSError("disk")
    reg = build_registry(lambda q, k: [], program_kaynagi=patlak, sinav_kaynagi=patlak,
                         takvim_kaynagi=patlak, icerik_kaynagi=patlak, not_kaynagi=patlak)
    for arac in YENI_ARACLAR:
        out = reg.dispatch(arac, {})
        assert not out.ok and "okunamadı" in out.error and "OSError" in out.error


def test_ogrenci_verisi_ara_aciklamasi_yeni_araclara_yonlendirir():
    tam = next(d for d in _tam_kayit().declarations() if d["name"] == at.LOCAL_TOOL)["description"]
    assert "`ders_programi`" in tam and "`sinavlar`" in tam
    # The old text promised "ödevler, sınavlar, notlar, ders programı, …" —
    # none of which the index held in readable form.
    assert "notlar, ders programı" not in tam
    # With no live source the description cannot point at tools that do not exist.
    yalin = next(d for d in build_registry(lambda q, k: []).declarations()
                 if d["name"] == at.LOCAL_TOOL)["description"]
    assert "`ders_programi`" not in yalin


def test_butun_govdeler_sinirin_altinda():
    uzun = "Uzun bir paragraf cümlesi, sayı doğrusu ve kesirler üzerine. " * 200
    buyuk_icerik = {"guncel": {f"Ders {i}": _icerik(uzun) for i in range(40)},
                    "haftalar": {}, "guncel_hafta": ""}
    buyuk_icerik["guncel"]["Matematik"] = _icerik(uzun, maddeler=[uzun[:300]] * 20, kartlar=[uzun] * 5)
    sinavlar = [{"id": str(i), "course": "Matematik", "title": f"Matematik · {i}. Yazılı",
                 "rawTitle": "7. Sınıflar Matematik Yazılı " + "x" * 200, "date": "2026-10-05T10:30:00",
                 "allDay": False, "status": "upcoming" if i % 2 else "past", "grade": "80"}
                for i in range(80)]
    etkinlikler = [{"id": str(i), "type": "event", "title": "Etkinlik " + "y" * 100,
                    "start": "2026-09-25T10:00:00", "end": "2026-09-25T11:00:00",
                    "description": "<p>" + "açıklama " * 60 + "</p>"} for i in range(100)]
    rubrikler = [{"ders": f"Ders {i % 9}", "alan": "ALAN", "kazanim": "Kazanım cümlesi " * 8,
                  "duzey": "Kazanımda"} for i in range(60)]
    reg = build_registry(
        lambda q, k: [], program_kaynagi=lambda: _kopya(HAFTA),
        sinav_kaynagi=lambda: sinavlar, takvim_kaynagi=lambda: etkinlikler,
        icerik_kaynagi=lambda: buyuk_icerik,
        not_kaynagi=lambda: {"gelisim": dict(GELISIM, rubrics=rubrikler), "ogretim_yili": "2026-2027"},
        saat=lambda: datetime(2026, 9, 24, 7, 0, tzinfo=UTC))
    for arac, args in ((at.PROGRAM_TOOL, {}), (at.SINAV_TOOL, {}), (at.TAKVIM_TOOL, {}),
                       (at.ICERIK_TOOL, {}), (at.ICERIK_TOOL, {"ders": "Matematik"}),
                       (at.NOT_TOOL, {})):
        out = reg.dispatch(arac, args)
        assert out.ok, (arac, out.error)
        assert len(out.text) <= GOVDE_SINIRI, (arac, len(out.text))


# ── 7. Runtime and dashboard wiring ─────────────────────────────────────────

def test_runtime_kaynaklari_registrye_iletir(tmp_path):
    from src.assistant_core import AssistantRuntime
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path, program_kaynagi=lambda: _kopya(HAFTA),
                          icerik_kaynagi=lambda: _kopya(ICERIK))
    adlar = {d["name"] for d in rt.registry.declarations()}
    assert {at.PROGRAM_TOOL, at.ICERIK_TOOL} <= adlar
    assert at.SINAV_TOOL not in adlar


def test_panonun_asistani_butun_kaynaklarla_kurulur(api, monkeypatch):
    import src.assistant_core as core
    alinan = {}

    class Sahte:
        def __init__(self, root, **kw):
            alinan.update(kw)
    monkeypatch.setattr(core, "AssistantRuntime", Sahte)
    monkeypatch.setattr(api, "_ASSISTANT_RUNTIME", None)
    api._assistant_runtime()
    assert alinan == {"odev_kaynagi": api._canli_odevler, "program_kaynagi": api._canli_program,
                      "sinav_kaynagi": api._canli_sinavlar, "takvim_kaynagi": api._canli_takvim,
                      "icerik_kaynagi": api._canli_ders_icerikleri,
                      "not_kaynagi": api._canli_notlar,
                      # plan Görev 3 (test_assistant_yerel_kaynaklar.py owns these sources' own
                      # behaviour; this test only pins that _assistant_runtime() wires them in)
                      "sebit_kaynagi": api._canli_sebit_odevleri,
                      "platform_kaynagi": api._canli_platform_ilerlemesi,
                      "kitap_kaynagi": api._canli_kitaplar,
                      "video_kaynagi": api._canli_videolar}


def test_canli_program_api_schedule_ile_ayni_haftayi_verir(api, monkeypatch):
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    with api.app.test_client() as c:
        rota = c.get("/api/schedule").get_json()["latest"]
    assert api._canli_program() == rota
    assert rota["schedule"]["rows"][1][1] == "Türkçe\nDeneme Öğretmen"     # normalised as before


def test_canli_icerik_ve_notlar_kaynaklari(api, monkeypatch):
    veri = {"ders_programi": [_kopya(HAFTA)], "ders_icerikleri": _kopya(GUNCEL),
            "ders_icerikleri_haftalar": _kopya(HAFTALAR), "gelisim_raporu": _kopya(GELISIM)}
    monkeypatch.setattr(api, "_scraped", lambda: _kopya(veri))
    with api.app.test_client() as c:
        haftalar = c.get("/api/content/weeks").get_json()
        notlar = c.get("/api/grades").get_json()
    icerik = api._canli_ders_icerikleri()
    assert icerik["haftalar"] == haftalar["weeks"] and icerik["guncel_hafta"] == haftalar["current"]
    assert icerik["guncel"] == GUNCEL
    monkeypatch.setattr(api, "_load_json", lambda ad: {"year": "2026-2027"} if ad == "academic_year.json" else {})
    assert api._canli_notlar() == {"gelisim": notlar, "ogretim_yili": "2026-2027"}


def test_sistem_istemi_yeni_araclara_yonlendirir():
    from src.assistant_core import AssistantRuntime
    p = AssistantRuntime.SYSTEM_PROMPT
    for arac in YENI_ARACLAR:
        assert f"`{arac}`" in p, arac
    assert "eski yılın notunu bu yılınki gibi sunma" in p
    assert "ogrenci_verisi_ara" in p


# ── 8. The formatter: what BM25 indexes from scraped_data.json ─────────────

def _tam_veri():
    return {
        "scraped_at": "2026-09-24T16:00:00",
        "ogrenci_profili": {"name": "Uydurma Öğrenci", "student_no": "99999",
                            "class_name": "7-Z", "branch": "Z",
                            "fields": {"Okul No": "99999", "Telefon": "0000 000 00 00",
                                       "Velisi (Anne)": "Hayali Veli"},
                            "photo_data_url": "data:image/png;base64,AAAA",
                            "profile_url": "https://portal.example/profil",
                            "email": "uydurma@example.invalid", "tc_kimlik": "00000000000"},
        "ders_programi": [_kopya(HAFTA)],
        "odevlerim": {"homework": {"rows": [
            {"Ders Adı": "Matematik", "Ödev Başlığı": "Tam sayılar testi",
             "Ödev Son Teslim Tarihi": "28.09.2026 12:00", "Ödev Durumu": "Değerlendirilmemiş",
             "detail": {"description": "Test 3 sayfa 20", "attachments": []}}]}},
        "takvim": [
            _etkinlik("Kulüp Tanıtımları", "2026-09-24T12:40:00+03:00", "2026-09-24T14:10:00+03:00",
                      aciklama="<p>Kulüp Tanıtımları</p>"),
            _etkinlik("Cumhuriyet Bayramı Töreni", "2026-10-29T08:00:00+03:00", "2026-10-29T12:00:00+03:00",
                      aciklama="<p>Tören&nbsp;spor salonunda yapılacak.</p>", yer="Spor Salonu"),
        ],
        "ders_icerikleri": _kopya(GUNCEL),
        "ders_icerikleri_haftalar": _kopya(HAFTALAR),
        "gelisim_raporu": _kopya(GELISIM),
        "ogep": {"sessions": {"headers": [], "rows": [], "empty_state": True}},
        "takim_calismalari": {"activities": {"headers": [], "rows": [], "empty_state": True}},
        "duyurular": {"announcements": []},
        "ek_sayfalar": {
            "ders_projeleri": {"title": "Ders Projeleri", "url": "https://portal.example/p",
                               "text": "Proje teslimi 1 Kasım'da başlayacak: bilim fuarı.",
                               "tables": [], "documents": [], "options": [], "empty": False},
            "kulup_secimi": {"title": "Kulüp Seçimi", "url": "https://portal.example/k",
                             "text": "Giriş sayfası artığı metin", "tables": [], "documents": [],
                             "options": [], "empty": True},
        },
    }


def _bicim():
    from src.assistant_core import _fmt_scraped_data
    return _fmt_scraped_data(_tam_veri())


def test_bicimlendirici_ders_programi_satirlarini_yazar():
    metin = _bicim()
    assert "Cuma · 2. ders 09:00–09:40 Fen Bilimleri" in metin
    assert "Pazartesi · 2. ders 08:55–09:35 Fransızca" in metin
    assert "Perşembe · 3. ders 09:45–10:25 Din Kültürü" in metin


def test_bicimlendirici_ders_icerigi_metnini_ve_haftalari_yazar():
    metin = _bicim()
    assert "(güncel okuma)" in metin                      # the open week
    assert "RASYONEL SAYILAR" in metin and "3. Hafta 28 Eyl. - 04 Eki." in metin
    assert "GÜNEŞ SİSTEMİ" in metin                       # fell back from the failed read
    assert "Mutlak değeri keşfedeceğiz" in metin          # items
    # The open week is read once: this run's read shadows the stored copy.
    assert "Sayı doğrusunda tam sayıları inceleyeceğiz." in metin
    assert metin.count("İlk yorum yapan") == 0
    assert "Stacktrace" not in metin and "Uydurma Öğrenci Adı" not in metin


def test_bicimlendirici_rubrik_takvim_ek_sayfa_ve_profil():
    metin = _bicim()
    assert "Denge becerilerini sergiler." in metin and "Kazanımın Üstünde" in metin
    assert "Tören spor salonunda yapılacak." in metin and "<p>" not in metin
    assert metin.count("Kulüp Tanıtımları") == 1          # description repeating the title dropped
    assert "bilim fuarı" in metin and "Giriş sayfası artığı" not in metin
    assert "7-Z" in metin and "TED Rönesans Koleji" in metin
    for sizmasin in ("uydurma@example.invalid", "00000000000", "99999", "0000 000 00 00",
                     "Hayali Veli", "Uydurma Öğrenci", "base64"):
        assert sizmasin not in metin, sizmasin


def test_bm25_ders_programini_ve_icerigi_bulur(tmp_path, monkeypatch):
    from src.assistant_core import AssistantRuntime
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "scraped_data.json").write_text(
        json.dumps(_tam_veri(), ensure_ascii=False), encoding="utf-8")
    rt = AssistantRuntime(tmp_path)
    rt.reindex(incremental=False)
    cuma = rt._local_search("ders programı cuma", 3)
    assert any("09:00–09:40 Fen Bilimleri" in h["text"] for h in cuma)
    rasyonel = rt._local_search("rasyonel sayılar matematik", 3)
    assert any("RASYONEL SAYILAR" in h["text"] for h in rasyonel)
