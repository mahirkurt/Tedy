"""SEBİT homework, Tedy Books search, platform progress and video suggestions
for the assistant (plan Görev 3, docs/superpowers/notes/
2026-09-25-asistan-veri-denetimi.md §1, §3).

Before this: `sebit_homework.json` (32 SEBİT assignments) never reached
`odev_listesi`; `books/` (Tedy Books' own chapters) was outside the file
index entirely (`DEFAULT_INCLUDE_DIRS`); EnglishCentral/Achieve3000 progress
reached the model only as raw JSON when it reached it at all; and
`mebi_videos_discovered.json` (112) / `sebitv_discovered.json` (657) were
invisible ("Görünmez" per the audit) — no route or index read either file.

Every fixture below has the real shape of its source file and invented
values: no real names, teachers, e-mails, ids or scores.
"""
import os
from datetime import datetime

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import assistant_kitaplar as ak  # noqa: E402
from src import assistant_tools as at  # noqa: E402
from src.assistant_tools import build_registry, odev_listesi_metni  # noqa: E402

GOVDE_SINIRI = 3900
SIMDI = datetime(2026, 9, 24, 16, 10)   # Perşembe


def _bolum(metin, baslik):
    """The lines under one heading, up to the next blank line."""
    basla = metin.index(baslik)
    son = metin.find("\n\n", basla)
    return metin[basla: son if son != -1 else None]


# ── 1. SEBİT: a section inside odev_listesi ─────────────────────────────────

def _hw(ders, baslik, teslim):
    return {"Ders Adı": ders, "normalized_course": ders, "Ödev Başlığı": baslik,
            "Ödev Son Teslim Tarihi": teslim, "Ödev Durumu": "",
            "student_marked_done": False, "teacher_resolved": False,
            "detail": {"description": "", "attachments": []}}


ROWS = [_hw("Matematik", "Test 1", "28.09.2026 12:00")]

SEBIT_VERI = {
    "scraped_at": "2026-09-20T10:00:00",
    "total_homework": 3,
    "completed_count": 1,
    "courses": ["Fen Bilimleri", "Sosyal Bilgiler"],
    "homework": [
        {"id": "s1", "list_id": "l1", "title": "Deneme Çalışması", "course_code": "fen",
         "course": "Fen Bilimleri", "progress": 40.0, "completed": False, "state": 2,
         "state_text": "Devam Ediyor", "teacher": "Deneme Öğretmen", "classes": "6/C",
         "start_date": "2026-09-10 08:00", "end_date": "2026-09-30 23:59"},
        {"id": "s2", "list_id": "l2", "title": "Örnek Deneme", "course_code": "sos",
         "course": "Sosyal Bilgiler", "progress": 100.0, "completed": True, "state": 2,
         "state_text": "Süresi Doldu", "teacher": "Uydurma Öğretmen", "classes": "6/A",
         "start_date": "2026-08-01 08:00", "end_date": "2026-08-15 23:59"},
        {"id": "s3", "list_id": "l3", "title": "Bitmemiş İş", "course_code": "fen",
         "course": "Fen Bilimleri", "progress": 10.0, "completed": False, "state": 1,
         "state_text": "Süresi Doldu", "teacher": "Deneme Öğretmen", "classes": "6/C",
         "start_date": "2026-09-01 08:00", "end_date": "2026-09-15 23:59"},
    ],
}


def test_sebit_verilmezse_bolum_yok():
    metin = odev_listesi_metni(ROWS, SIMDI)
    assert "SEBİT" not in metin


def test_sebit_bolumu_acik_ve_tamamlanani_ayirir():
    metin = odev_listesi_metni(ROWS, SIMDI, sebit=SEBIT_VERI)
    acik = _bolum(metin, "SEBİT — AÇIK")
    assert "Deneme Çalışması" in acik and "Bitmemiş İş" in acik
    assert "Örnek Deneme" not in acik          # completed, not listed individually
    assert "SEBİT — TAMAMLANDI (1)" in metin
    # existing sections are untouched
    assert "YAPILACAK" in metin and "Test 1" in _bolum(metin, "YAPILACAK")


def test_sebit_bitis_tarihi_ve_yuzdesi_yazilir():
    metin = odev_listesi_metni(ROWS, SIMDI, sebit=SEBIT_VERI)
    acik = _bolum(metin, "SEBİT — AÇIK")
    assert "Fen Bilimleri — Deneme Çalışması" in acik
    assert "%40" in acik
    assert "Çarşamba 30.09.2026 23:59" in acik and "gün sonra" in acik


def test_sebit_bos_liste_bunu_soyler():
    bos = {"homework": []}
    assert "SEBİT'te kayıtlı ödev yok" in odev_listesi_metni(ROWS, SIMDI, sebit=bos)


def test_odev_listesi_bos_olsa_bile_sebit_eklenir():
    metin = odev_listesi_metni([], SIMDI, sebit=SEBIT_VERI)
    assert "portalda kayıtlı ödev yok" in metin
    assert "SEBİT — AÇIK" in metin


def test_arac_sebit_kaynagiyla_baglanir_ve_kaynak_hatasi_ana_listeyi_bozmaz():
    reg = build_registry(lambda q, k: [], odev_kaynagi=lambda: ROWS,
                         sebit_kaynagi=lambda: SEBIT_VERI)
    out = reg.dispatch(at.ODEV_TOOL, {})
    assert out.ok, out.error
    assert "SEBİT — AÇIK" in out.text and "Test 1" in out.text

    def patlar():
        raise RuntimeError("sebit kırık")
    reg2 = build_registry(lambda q, k: [], odev_kaynagi=lambda: ROWS, sebit_kaynagi=patlar)
    out2 = reg2.dispatch(at.ODEV_TOOL, {})
    assert out2.ok, out2.error                 # SEBİT's own failure is soft
    assert "Test 1" in out2.text and "SEBİT" not in out2.text


def test_arac_sebit_kaynagi_yoksa_odev_listesi_degismez():
    reg = build_registry(lambda q, k: [], odev_kaynagi=lambda: ROWS)
    out = reg.dispatch(at.ODEV_TOOL, {})
    assert out.ok and "SEBİT" not in out.text


# ── 2. kitap_ara: Tedy Books search ─────────────────────────────────────────

KITAPLAR = [
    {"slug": "deneme-kitap", "title": "Deneme Kitabı", "chapters": [
        {"id": "B01", "title": "Bölüm Bir",
         "text": ("Uydurma kahraman ormanda yürüdü ve parlayan bir taş buldu orada.\n\n"
                  "Taşı cebine koydu ve köyüne doğru koşmaya başladı hemen.")},
        {"id": "B02", "title": "Bölüm İki",
         "text": ("Ertesi gün kahraman taşı köyün yaşlı büyücüsüne gösterdi merakla.\n\n"
                  "Büyücü taşın çok eski ve gizemli bir yüzük olduğunu söyledi ona.")},
    ]},
    {"slug": "ikinci-kitap", "title": "İkinci Kitap", "chapters": [
        {"id": "B01", "title": "Başlangıç",
         "text": ("Farklı bir hikaye burada başlıyor, deniz kenarında sakin bir kasabada.\n\n"
                  "Kasabanın çocukları her yaz sabahı balık tutmaya giderdi birlikte.")},
    ]},
]


def test_kitap_araci_yalniz_kaynak_verilince_sunulur():
    assert ak.TOOL_NAME not in [d["name"] for d in build_registry(lambda q, k: []).declarations()]
    reg = build_registry(lambda q, k: [], kitap_kaynagi=lambda: KITAPLAR)
    decl = next(d for d in reg.declarations() if d["name"] == ak.TOOL_NAME)
    assert decl["parameters"]["required"] == ["sorgu"]


def test_pasaj_kitap_ve_bolum_adiyla_doner():
    reg = build_registry(lambda q, k: [], kitap_kaynagi=lambda: KITAPLAR)
    out = reg.dispatch(ak.TOOL_NAME, {"sorgu": "gizemli yüzük"})
    assert out.ok, out.error
    assert "Deneme Kitabı" in out.text and "büyücü" in out.text.lower()
    assert out.citations, out.citations
    etiketler = [c["label"] for c in out.citations]
    assert "Deneme Kitabı · Bölüm İki" in etiketler
    assert all(c["kind"] == "tedy-kitap" for c in out.citations)
    # reader-facing labels: no internal path
    assert all("/" not in c["label"] and ".md" not in c["label"] for c in out.citations)


def test_kitap_filtresi_baska_kitabi_disarida_birakir():
    reg = build_registry(lambda q, k: [], kitap_kaynagi=lambda: KITAPLAR)
    out = reg.dispatch(ak.TOOL_NAME, {"sorgu": "kasabada balık tutmak", "kitap": "Deneme Kitabı"})
    assert out.ok, out.error
    assert "İkinci Kitap" not in out.text
    assert "eşleşen pasaj bulunamadı" in out.text or out.citations == []


def test_kitap_adi_eslesmezse_mevcut_kitaplari_soyler():
    reg = build_registry(lambda q, k: [], kitap_kaynagi=lambda: KITAPLAR)
    out = reg.dispatch(ak.TOOL_NAME, {"sorgu": "her şey", "kitap": "Olmayan Kitap"})
    assert out.ok, out.error
    assert "Deneme Kitabı" in out.text and "İkinci Kitap" in out.text
    assert out.citations == []


def test_kitap_sorgu_bossa_bilgilendirir():
    reg = build_registry(lambda q, k: [], kitap_kaynagi=lambda: KITAPLAR)
    out = reg.dispatch(ak.TOOL_NAME, {"sorgu": ""})
    assert out.ok and out.citations == []


def test_kitap_govde_siniri_asilmaz():
    buyuk = [{"slug": "buyuk", "title": "Büyük Kitap", "chapters": [
        {"id": f"B{i:02d}", "title": f"Bölüm {i}",
         "text": ("Taş ve yüzük hakkında uzun bir paragraf burada tekrar tekrar yazılıyor. " * 20)}
        for i in range(1, 8)
    ]}]
    reg = build_registry(lambda q, k: [], kitap_kaynagi=lambda: buyuk)
    out = reg.dispatch(ak.TOOL_NAME, {"sorgu": "taş yüzük"})
    assert out.ok
    assert len(out.text) <= GOVDE_SINIRI


# ── 3. platform_ilerlemesi ───────────────────────────────────────────────────

EC_VERI = {
    "scraped_at": "2026-09-20T10:00:00",
    "class_name": "7A", "class_id": 1001,
    "total_videos": 4, "completed_videos": 2,
    "videos": [
        {"dialog_id": 1, "title": "Uydurma Video Bir", "url": "https://example.invalid/1",
         "difficulty": 3, "duration": "00:01:00", "completed": True, "started": True,
         "activities": {}},
        {"dialog_id": 2, "title": "Uydurma Video İki", "url": "https://example.invalid/2",
         "difficulty": 6, "duration": "00:02:00", "completed": True, "started": True,
         "activities": {}},
        {"dialog_id": 3, "title": "Uydurma Video Üç", "url": "https://example.invalid/3",
         "difficulty": 7, "duration": "00:00:45", "completed": False, "started": False,
         "activities": {}},
        {"dialog_id": 4, "title": "Uydurma Video Dört", "url": "https://example.invalid/4",
         "difficulty": 2, "duration": "00:01:30", "completed": False, "started": True,
         "activities": {}},
    ],
}
A3K_VERI = {
    "scraped_at": "2026-09-19T09:00:00",
    "class_name": "7A 25-26",
    "dashboard_stats": {"scoredAboveLine": 5, "completed": 3, "target": 40, "firstTryScore": 62},
    "total_lessons": 100, "teacher_assigned_count": 5, "teacher_assigned_completed": 3,
    "lessons": [
        {"title": "Uydurma Ders Bir", "url": "https://example.invalid/a", "category": "Bilim",
         "score": 80, "completed": True, "completed_steps": 5, "total_steps": 5,
         "is_teacher_assigned": True},
        {"title": "Uydurma Ders İki", "url": "https://example.invalid/b", "category": "Sosyal",
         "score": 0, "completed": False, "completed_steps": 1, "total_steps": 5,
         "is_teacher_assigned": True},
    ],
}


def test_platform_araci_yalniz_kaynak_verilince_sunulur():
    assert at.PLATFORM_TOOL not in [d["name"] for d in build_registry(lambda q, k: []).declarations()]
    reg = build_registry(lambda q, k: [], platform_kaynagi=lambda: {})
    assert at.PLATFORM_TOOL in [d["name"] for d in reg.declarations()]


def test_platform_ozeti_tamamlanani_kalani_ve_duzeyi_yazar():
    reg = build_registry(lambda q, k: [], platform_kaynagi=lambda: {"ec": EC_VERI, "a3k": A3K_VERI})
    out = reg.dispatch(at.PLATFORM_TOOL, {})
    assert out.ok, out.error
    assert "2/4 video tamamlandı" in out.text
    assert "Uydurma Video Üç" in out.text and "düzey 7" in out.text
    assert "Uydurma Video Bir" not in out.text     # completed; not among "remaining"
    assert "3/5 ders tamamlandı" in out.text
    assert "Uydurma Ders İki" in out.text
    assert "62" in out.text                          # first-try score
    assert out.citations[0]["label"] == "Platform ilerlemesi"


def test_platform_veri_okunma_zamanini_soyler_uydurmaz():
    reg = build_registry(lambda q, k: [], platform_kaynagi=lambda: {"ec": EC_VERI, "a3k": A3K_VERI})
    out = reg.dispatch(at.PLATFORM_TOOL, {})
    assert "okundu" in out.text
    assert "20.09.2026" in out.text                  # EC's own scraped_at


def test_platform_bos_veri_cokmeden_soyler():
    reg = build_registry(lambda q, k: [], platform_kaynagi=lambda: {})
    out = reg.dispatch(at.PLATFORM_TOOL, {})
    assert out.ok, out.error
    assert "ENGLISHCENTRAL" in out.text and "yok" in out.text
    assert "ACHIEVE3000" in out.text


def test_platform_govde_siniri_asilmaz():
    reg = build_registry(lambda q, k: [], platform_kaynagi=lambda: {"ec": EC_VERI, "a3k": A3K_VERI})
    out = reg.dispatch(at.PLATFORM_TOOL, {})
    assert len(out.text) <= GOVDE_SINIRI


# ── 4. video_oner ─────────────────────────────────────────────────────────

MEBI = [
    {"course": "Matematik", "unit": "Kesirler", "topic": "Kesirlerde Toplama",
     "uuid": "uuid-1", "cdnUrl": "https://cdn.example.invalid/video1.mp4"},
    {"course": "Fen Bilimleri", "unit": "Ölçüm", "topic": "Kesirli Ölçüm Deneyleri",
     "uuid": "uuid-3", "cdnUrl": ""},
]
SEBITV = [
    {"course": "Matematik", "unit": "Kesirler", "topic": "Kesirlerde Çıkarma",
     "subSubject": "Kesirlerde Çıkarma İşlemi", "resourceId": "r1", "code": "TRM01",
     "version": 1, "title": "Kesir Dünyası", "fileType": "zip", "duration": 30.0,
     "fileSize": 1000, "type": "Konu Anlatımı", "lessonPlanId": ""},
    {"course": "Türkçe", "unit": "Cümlede Anlam", "topic": "Öznel-Nesnel Anlatım",
     "subSubject": "", "resourceId": "r2", "code": "TRM02", "version": 1,
     "title": "Cümle Oyunu", "fileType": "zip", "duration": 12.0, "fileSize": 500,
     "type": "Konu Anlatımı", "lessonPlanId": ""},
]


def test_video_araci_yalniz_kaynak_verilince_sunulur():
    assert at.VIDEO_TOOL not in [d["name"] for d in build_registry(lambda q, k: []).declarations()]
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": [], "sebitv": []})
    assert at.VIDEO_TOOL in [d["name"] for d in reg.declarations()]


def test_video_konuya_gore_arar_baslik_ders_ve_baglanti_doner():
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": MEBI, "sebitv": SEBITV})
    out = reg.dispatch(at.VIDEO_TOOL, {"konu": "kesir"})
    assert out.ok, out.error
    assert "Kesirlerde Toplama" in out.text and "Kesirlerde Çıkarma" in out.text
    assert "https://cdn.example.invalid/video1.mp4" in out.text     # MEBİ: real link
    assert out.text.count("Bağlantı:") == 1              # only the one item with a real cdnUrl
    assert all(c["kind"] == "ogrenci" for c in out.citations)


def test_video_ders_filtresi_daraltir():
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": MEBI, "sebitv": SEBITV})
    genis = reg.dispatch(at.VIDEO_TOOL, {"konu": "kesir"})
    daraltilmis = reg.dispatch(at.VIDEO_TOOL, {"konu": "kesir", "ders": "Matematik"})
    assert "Kesirli Ölçüm Deneyleri" in genis.text
    assert "Kesirli Ölçüm Deneyleri" not in daraltilmis.text
    assert "Kesirlerde Toplama" in daraltilmis.text


def test_video_esleme_yoksa_bilgilendirir():
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": MEBI, "sebitv": SEBITV})
    out = reg.dispatch(at.VIDEO_TOOL, {"konu": "uzaylılar"})
    assert out.ok, out.error
    assert "bulunamadı" in out.text and out.citations == []


def test_video_sinif_bilgisi_olmadigini_soyler():
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": MEBI, "sebitv": SEBITV})
    out = reg.dispatch(at.VIDEO_TOOL, {"konu": "kesir"})
    assert "sınıf bilgisi yok" in out.text


def test_video_etiketler_okunur_ic_kimlik_tasimaz():
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": MEBI, "sebitv": SEBITV})
    out = reg.dispatch(at.VIDEO_TOOL, {"konu": "kesir"})
    for c in out.citations:
        assert "uuid" not in c["label"] and "resourceId" not in c["label"]


def test_video_govde_siniri_asilmaz():
    reg = build_registry(lambda q, k: [], video_kaynagi=lambda: {"mebi": MEBI, "sebitv": SEBITV})
    out = reg.dispatch(at.VIDEO_TOOL, {"konu": "kesir"})
    assert len(out.text) <= GOVDE_SINIRI


# ── 5. Runtime and dashboard wiring ─────────────────────────────────────────

def test_runtime_yeni_kaynaklari_registrye_iletir(tmp_path):
    from src.assistant_core import AssistantRuntime
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path, sebit_kaynagi=lambda: SEBIT_VERI,
                          platform_kaynagi=lambda: {}, kitap_kaynagi=lambda: KITAPLAR,
                          video_kaynagi=lambda: {"mebi": [], "sebitv": []})
    adlar = {d["name"] for d in rt.registry.declarations()}
    assert {at.PLATFORM_TOOL, ak.TOOL_NAME, at.VIDEO_TOOL} <= adlar


def test_panonun_asistani_yeni_kaynaklarla_kurulur(monkeypatch):
    import src.assistant_core as core
    import src.dashboard_api as api
    alinan = {}

    class Sahte:
        def __init__(self, root, **kw):
            alinan.update(kw)
    monkeypatch.setattr(core, "AssistantRuntime", Sahte)
    monkeypatch.setattr(api, "_ASSISTANT_RUNTIME", None)
    api._assistant_runtime()
    assert alinan["sebit_kaynagi"] is api._canli_sebit_odevleri
    assert alinan["platform_kaynagi"] is api._canli_platform_ilerlemesi
    assert alinan["kitap_kaynagi"] is api._canli_kitaplar
    assert alinan["video_kaynagi"] is api._canli_videolar


def test_canli_sebit_odevleri_apinin_kaynagini_okur(monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_load_json", lambda ad: dict(SEBIT_VERI) if ad == "sebit_homework.json" else {})
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        rota = c.get("/api/sebit").get_json()
    assert api._canli_sebit_odevleri() == rota


def test_canli_platform_ilerlemesi_ec_ve_a3k_rotalariyla_ayni(monkeypatch):
    import src.dashboard_api as api

    def sahte_yukle(ad):
        if ad == "englishcentral_progress.json":
            return EC_VERI
        if ad == "achieve3000_progress.json":
            return A3K_VERI
        return {}
    monkeypatch.setattr(api, "_load_json", sahte_yukle)
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        ec_rota = c.get("/api/progress/ec").get_json()
        a3k_rota = c.get("/api/progress/a3k").get_json()
    canli = api._canli_platform_ilerlemesi()
    assert canli == {"ec": ec_rota, "a3k": a3k_rota}


def test_canli_videolar_liste_disini_bosa_indirger(monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_load_json", lambda ad: {"beklenmedik": "sekil"})
    assert api._canli_videolar() == {"mebi": [], "sebitv": []}


def test_canli_kitaplar_bolum_metnini_on_madde_olmadan_doner(tmp_path, monkeypatch):
    import src.dashboard_api as api
    books_dir = tmp_path / "books"
    (books_dir / "deneme-kitap").mkdir(parents=True)
    (books_dir / "deneme-kitap" / "B01_Bolum.md").write_text(
        "# Birinci Kısım\n## Bölüm Bir\n*Deneme Yazar*\n---\n\nAsıl gövde metni burada başlıyor.\n",
        encoding="utf-8")
    monkeypatch.setattr(api, "BOOKS_DIR", str(books_dir))
    kitaplar = api._canli_kitaplar()
    assert kitaplar and kitaplar[0]["slug"] == "deneme-kitap"
    bolum = kitaplar[0]["chapters"][0]
    assert bolum["title"]                       # from manifest fallback / filename
    assert "Asıl gövde metni" in bolum["text"]
    assert "Birinci Kısım" not in bolum["text"]  # front matter stripped, as the reader sees it


# ── 6. System prompt routes to the new tools ────────────────────────────────

YENI_ARACLAR = ("kitap_ara", "platform_ilerlemesi", "video_oner")


def test_sistem_istemi_yeni_araclara_yonlendirir():
    from src.assistant_core import AssistantRuntime
    p = AssistantRuntime.SYSTEM_PROMPT
    for arac in YENI_ARACLAR:
        assert f"`{arac}`" in p, arac
