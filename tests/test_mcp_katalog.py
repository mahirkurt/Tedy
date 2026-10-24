"""Catalog writer and publish tools: immutable versions, EXAM/FAIL refusal, soft removal, concurrency."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import anyio
import pytest

from src import module_store as ms
from src.json_utils import atomic_json_dump
from src.mcp_server import ornekler, server, tools
from src.mcp_server.config import load_settings
from src.mcp_server.derle_araci import Derleyici
from src.mcp_server.katalog import CatalogWriter, Yayinci, slug_turet
from src.mcp_server.runs import RunStore
from src.mcp_server.taslak import DraftStore

FULL = "drmahirkurt@gmail.com"
RUN_ID = "abcdef012345"
NOW = 1_800_000_000.0
RUN_RECORD = {
    "run_id": RUN_ID, "created_by": FULL,
    "cerceve": {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"},
    "kazanimlar": [{"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar."}],
    "coverage": {"maarif-mufredat": "hit"},
}
SLUG = "fen5-maddenin-halleri-ve-su-dongusu"


@pytest.fixture
def env(tmp_path):
    runs = RunStore(tmp_path)
    runs.save(RUN_ID, RUN_RECORD)
    drafts = DraftStore(tmp_path)
    derleyici = Derleyici(runs, drafts, "https://tedy.online", "https://tedy.online", clock=lambda: NOW)
    return tmp_path, derleyici, Yayinci(drafts, CatalogWriter(tmp_path, clock=lambda: NOW), "https://tedy.online")


def _taslak(derleyici, mode="QUIZ", mutate=None):
    data = ornekler.ornek(mode)
    if mutate:
        mutate(data)
    return derleyici.derle(FULL, RUN_ID, data)["taslak_id"]


def test_slug_derivation_folds_turkish():
    assert slug_turet("Fen Bilimleri", "5. Sınıf", "Maddenin Hâlleri ve Su Döngüsü") == SLUG
    assert slug_turet("Matematik", "6. Sınıf", "Kesirler: Toplama & Çıkarma") == "mat6-kesirler-toplama-cikarma"
    assert len(slug_turet("Fen Bilimleri", "5", "a" * 200)) <= 60
    assert slug_turet("", "", "!!!") == "modul"


def test_publish_writes_an_immutable_version_and_a_catalog_record(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    body = yayinci.yayinla(FULL, taslak_id, ted_link={"kind": "exam", "id": "ex-42"})
    assert body == {"status": "ok", "slug": SLUG, "version": 1,
                    "url": f"https://tedy.online/moduller/{SLUG}/v1", "arsivlenen_surumler": [], "mcp_verified": False}
    drafts = DraftStore(tmp_path)
    html = ms.module_html_path(tmp_path, SLUG, 1).read_bytes()
    record = ms.find_record(tmp_path, SLUG, 1)
    assert html == drafts.html_bytes(taslak_id)
    assert record["sha256"] == drafts.load(taslak_id)["sha256"] == hashlib.sha256(html).hexdigest()
    assert record["status"] == "active" and record["mode"] == "QUIZ" and record["outcomes"] == ["FB.5.4.1.1"]
    assert record["ted_link"] == {"kind": "exam", "id": "ex-42"} and record["created_by"] == FULL
    assert record["gates"]["fail"] == 0 and record["frame_source"]["document_id"] == 197
    assert record["taslak_id"] == taslak_id and record["run_id"] == RUN_ID and record["bytes"] == len(html)
    assert yayinci.yayinla(FULL, taslak_id)["version"] == 2
    assert ms.find_record(tmp_path, SLUG, 1)["sha256"] == record["sha256"]


def test_explicit_slug_rules(env):
    _, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    assert yayinci.yayinla(FULL, taslak_id, slug="taslak")["status"] == "gecersiz_slug"
    assert yayinci.yayinla(FULL, taslak_id, slug="../x")["status"] == "gecersiz_slug"
    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-su")["slug"] == "fen5-su"


def test_refusals(env):
    _, derleyici, yayinci = env
    failing = _taslak(derleyici, "MODULE", lambda d: d["verification"]["scope"].__setitem__("in_frame", False))
    body = yayinci.yayinla(FULL, failing)
    assert body["status"] == "kapi_fail" and "G-VERIFY" in body["fail_kapilari"]
    assert yayinci.yayinla(FULL, _taslak(derleyici, "EXAM"))["status"] == "yayin_yok_exam_modu"
    assert yayinci.yayinla(FULL, "ffffffffffffffff")["status"] == "taslak_bulunamadi"
    assert yayinci.yayinla(FULL, _taslak(derleyici), ted_link={"kind": "quiz", "id": "1"})["status"] == "gecersiz_ted_link"


def test_tampered_draft_is_not_published(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    ms.draft_html_path(tmp_path, taslak_id).write_bytes(b"<html>degisti</html>")
    assert yayinci.yayinla(FULL, taslak_id)["status"] == "taslak_bozuk"


def test_eski_taslak_bugunun_kapilarindan_gecmezse_yayinlanmaz(env):
    # Son inceleme, Küçük 11 (karar): birleşmeden önce derlenmiş taslak, kaydında PASS yazsa da yayından önce
    # bugünün kapılarından yeniden geçer; FAIL varsa yayınlanmaz ve hiçbir şey yazılmaz.
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    yol = ms.draft_html_path(tmp_path, taslak_id)
    baslik = ornekler.ornek("QUIZ")["meta"]["title"]
    html = yol.read_text(encoding="utf-8")
    assert baslik in html
    eski = html.replace(baslik, "Mini Yarışma").encode("utf-8")
    yol.write_bytes(eski)
    kayit_yolu = yol.with_name(ms.DRAFT_RECORD)
    kayit = json.loads(kayit_yolu.read_text(encoding="utf-8"))
    assert kayit["gates"]["fail"] == 0
    kayit.update(sha256=hashlib.sha256(eski).hexdigest(), bayt=len(eski))
    atomic_json_dump(kayit, str(kayit_yolu))
    body = yayinci.yayinla(FULL, taslak_id)
    assert body["status"] == "kapi_fail_guncel", body
    assert body["fail_kapilari"] == ["G-WELLBEING"]
    assert "yayınlanmadı" in body["not"] and "edupedia_derle" in body["not"]
    assert ms.read_catalog(tmp_path) == []
    assert not ms.modules_root(tmp_path).exists() or not any(ms.modules_root(tmp_path).iterdir())


def test_kapilar_yeniden_kosamazsa_yayin_durur(env, monkeypatch):
    """İkinci inceleme (Küçük a): yayından önceki kapı koşusu istisna atarsa yayın kapalı kalır — kapanmış
    sunucu_hatasi döner, istisnanın metni sızmaz, katalog ve sürüm dizini yazılmaz."""
    from src.mcp_server import gates

    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)

    def boom(html):
        raise RuntimeError("kapı düzeni bozuk: gizli ayrıntı")

    monkeypatch.setattr(gates, "run_gates", boom)
    body = yayinci.yayinla(FULL, taslak_id)
    assert body["status"] == "sunucu_hatasi", body
    assert "gizli" not in json.dumps(body, ensure_ascii=False)
    assert ms.read_catalog(tmp_path) == []
    assert not ms.modules_root(tmp_path).exists() or not any(ms.modules_root(tmp_path).iterdir())


def test_orphan_version_directory_is_skipped_not_overwritten(env):
    tmp_path, derleyici, yayinci = env
    orphan = ms.modules_root(tmp_path) / "fen5-su" / "v1"
    orphan.mkdir(parents=True)
    (orphan / "index.html").write_text("yarim", encoding="utf-8")
    assert yayinci.yayinla(FULL, _taslak(derleyici), slug="fen5-su")["version"] == 2
    assert (orphan / "index.html").read_text(encoding="utf-8") == "yarim"


def test_concurrent_publishes_get_distinct_versions(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: yayinci.yayinla(FULL, taslak_id, slug="fen5-su"), range(8)))
    assert sorted(r["version"] for r in results) == list(range(1, 9))
    rows = [r for r in ms.read_catalog(tmp_path) if r["slug"] == "fen5-su"]
    assert len(rows) == 8
    # Arşivleme (2026-10-24) aynı kilit altında: eşzamanlı yayınların sonunda yalnız en yeni sürüm yayında.
    assert [r["version"] for r in rows if r["status"] == "active"] == [8]
    assert sorted(v for r in results for v in r["arsivlenen_surumler"]) == list(range(1, 8))


def test_katalog_and_soft_removal(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    listed = yayinci.katalog(ders="fen", sinif="5")
    assert listed["status"] == "ok" and listed["sayi"] == 1 and listed["mcp_verified"] is False
    assert set(listed["moduller"][0]) == {"slug", "version", "status", "title", "subject", "gradeLevel", "mode",
                                          "outcomes", "ted_link", "gates", "created_at", "url"}
    assert yayinci.katalog(ders="matematik")["sayi"] == 0
    assert yayinci.katalog(durum="bilinmez")["status"] == "gecersiz_durum"
    removed = yayinci.kaldir(FULL, "fen5-su")
    assert removed["status"] == "ok" and removed["kaldirilan_surum_sayisi"] == 1
    assert yayinci.katalog()["sayi"] == 0 and yayinci.katalog(durum="removed")["sayi"] == 1
    # Kaldırma yayındakini düşürür; arşivlenmiş sürüm arşivde kalır (adresi "artık yayında değil" der).
    assert yayinci.katalog(durum="archived")["sayi"] == 1
    assert ms.module_html_path(tmp_path, "fen5-su", 1).is_file()
    row = ms.find_record(tmp_path, "fen5-su", 2)
    assert row["removed_by"] == FULL and row["removed_at"]
    assert yayinci.kaldir(FULL, "fen5-su")["status"] == "bulunamadi"
    assert yayinci.kaldir(FULL, "../x")["status"] == "gecersiz_slug"


# -- Fix round 1 -----------------------------------------------------------------------------

def test_next_version_ignores_malformed_catalog_rows(env):
    """F1: a corrupted `version` field (e.g. a disk edit gone wrong) must not crash version
    selection via an unguarded int() coercion; it is simply invisible to it."""
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    first = yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    assert first["status"] == "ok" and first["version"] == 1

    catalog_path = ms.catalog_path(tmp_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    data["moduller"].append({**data["moduller"][0], "version": "x"})
    atomic_json_dump(data, str(catalog_path))

    body = yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    assert body["status"] == "ok" and body["version"] == 2

    assert yayinci.katalog(durum="hepsi")["status"] == "ok"
    assert yayinci.kaldir(FULL, "fen5-su")["status"] == "ok"


def test_version_limit_returns_a_closed_status_carrying_the_limit(env, monkeypatch):
    """F2/F3: exceeding VERSION_MAX must not raise a raw ValueError out of Yayinci.yayinla."""
    tmp_path, derleyici, yayinci = env
    monkeypatch.setattr(ms, "VERSION_MAX", 2)
    taslak_id = _taslak(derleyici)
    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-su")["version"] == 1
    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-su")["version"] == 2
    body = yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    assert body["status"] == "surum_siniri" and body["sinir"] == 2 and body["taslak_id"] == taslak_id


def test_symlinked_slug_directory_is_rejected_and_nothing_is_written(env, tmp_path_factory):
    """F2/F3: module_html_path's containment rejection (e.g. a symlinked slug dir) must surface
    as its own status, not a mislabeled surum_siniri, and must never write outside the root."""
    tmp_path, derleyici, yayinci = env
    outside = tmp_path_factory.mktemp("outside")
    modules_root = ms.modules_root(tmp_path)
    modules_root.mkdir(parents=True, exist_ok=True)
    (modules_root / "fen5-su").symlink_to(outside, target_is_directory=True)
    taslak_id = _taslak(derleyici)

    body = yayinci.yayinla(FULL, taslak_id, slug="fen5-su")

    assert body["status"] == "yol_reddedildi"
    assert list(outside.iterdir()) == []


def test_unexpected_exception_from_catalog_write_becomes_closed_sunucu_hatasi(env, monkeypatch):
    """F3: an unrelated failure (e.g. ENOSPC) inside CatalogWriter.yayinla must reach the tool
    caller as a closed status, never as the exception's own text or type name."""
    _, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)

    def boom(*args, **kwargs):
        raise OSError("disk dolu /home/x")

    monkeypatch.setattr(yayinci.catalog, "yayinla", boom)
    body = yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    assert body["status"] == "sunucu_hatasi" and body["taslak_id"] == taslak_id
    dumped = json.dumps(body, ensure_ascii=False)
    assert "disk dolu" not in dumped and "OSError" not in dumped


def test_catalog_read_failure_becomes_closed_sunucu_hatasi_for_katalog_and_kaldir(env, monkeypatch):
    """F3: katalog() and kaldir() must close off any exception from the catalog read, too."""
    _, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    yayinci.yayinla(FULL, taslak_id, slug="fen5-su")

    def boom(*args, **kwargs):
        raise RuntimeError("iç ayrıntı")

    monkeypatch.setattr(ms, "read_catalog_with_status", boom)

    body_katalog = yayinci.katalog()
    assert body_katalog["status"] == "sunucu_hatasi"
    assert "iç ayrıntı" not in json.dumps(body_katalog, ensure_ascii=False)

    body_kaldir = yayinci.kaldir(FULL, "fen5-su")
    assert body_kaldir["status"] == "sunucu_hatasi" and body_kaldir["slug"] == "fen5-su"
    assert "iç ayrıntı" not in json.dumps(body_kaldir, ensure_ascii=False)


def test_fail_check_is_derived_from_kapilar_not_just_the_summary_count(env):
    """F4: a tampered draft record (gates.fail=0 but a FAIL entry still in kapilar) must still
    refuse — the FAIL check is fail-closed against the per-gate report, not the summary field."""
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    record_path = ms.draft_dir(tmp_path, taslak_id) / ms.DRAFT_RECORD
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["gates"]["fail"] == 0
    record["kapilar"] = {"G-VERIFY": {"status": "FAIL"}}
    atomic_json_dump(record, str(record_path))

    body = yayinci.yayinla(FULL, taslak_id)

    assert body["status"] == "kapi_fail" and "G-VERIFY" in body["fail_kapilari"]


def test_fail_check_refuses_when_kapilar_is_missing(env):
    """F4: a record with no kapilar at all is malformed, not proof of a clean gate report."""
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    record_path = ms.draft_dir(tmp_path, taslak_id) / ms.DRAFT_RECORD
    record = json.loads(record_path.read_text(encoding="utf-8"))
    del record["kapilar"]
    atomic_json_dump(record, str(record_path))

    body = yayinci.yayinla(FULL, taslak_id)

    assert body["status"] == "kapi_fail" and body["fail_kapilari"] == []


class _Fed:
    def configured(self, name):
        return False

    def call(self, *args, **kwargs):
        raise AssertionError("no fleet calls")


def test_tools_are_registered_with_honest_annotations(tmp_path):
    mcp = server.build_server(tools.Tools(load_settings({}, project_root=tmp_path), _Fed()))
    listed = {t.name: t for t in anyio.run(mcp.list_tools)}
    assert listed["edupedia_yayinla"].annotations.readOnlyHint is False
    assert listed["edupedia_kaldir"].annotations.destructiveHint is True
    assert listed["edupedia_katalog"].annotations.readOnlyHint is True
    arsivle = listed["edupedia_arsivle"].annotations
    assert arsivle.readOnlyHint is False and arsivle.destructiveHint is False and arsivle.openWorldHint is True
    assert "arşiv" in listed["edupedia_arsivle"].description


# -- Arşivleme (2026-10-24): eski sürümler yeni yayında arşivlenir ---------------------------------

def _katalogu_yaz(tmp_path, durumlar):
    """Arşivlemeden önceki katalog: aynı slug'ın birden çok `active` sürümü (canlıdaki hâl)."""
    path = ms.catalog_path(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data["moduller"]:
        key = (row["slug"], row["version"])
        if key in durumlar:
            row["status"] = durumlar[key]
            for alan in ("archived_at", "archived_by"):
                row.pop(alan, None)
    atomic_json_dump(data, str(path))


def test_yeni_yayin_ayni_slugin_onceki_active_surumlerini_arsivler(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-baska")["arsivlenen_surumler"] == []
    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-su")["arsivlenen_surumler"] == []
    body = yayinci.yayinla("isikkurtx@gmail.com", taslak_id, slug="fen5-su")
    assert body["status"] == "ok" and body["version"] == 2 and body["arsivlenen_surumler"] == [1]
    eski, yeni = ms.find_record(tmp_path, "fen5-su", 1), ms.find_record(tmp_path, "fen5-su", 2)
    assert eski["status"] == "archived" and eski["archived_by"] == "isikkurtx@gmail.com"
    assert eski["archived_at"] == yeni["created_at"]
    assert yeni["status"] == "active" and "archived_at" not in yeni
    assert ms.find_record(tmp_path, "fen5-baska", 1)["status"] == "active"
    # Dosya silinmez: arşivlenmiş sürümün HTML'i yerinde.
    assert ms.module_html_path(tmp_path, "fen5-su", 1).is_file()
    assert [(m["slug"], m["version"]) for m in yayinci.katalog()["moduller"]] == [("fen5-baska", 1), ("fen5-su", 2)]
    arsiv = yayinci.katalog(durum="archived")
    assert arsiv["status"] == "ok" and [(m["slug"], m["version"], m["status"]) for m in arsiv["moduller"]] == [
        ("fen5-su", 1, "archived")]
    assert yayinci.katalog(durum="hepsi")["sayi"] == 3


def test_arsivleme_kaldirilmis_surume_dokunmaz(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    yayinci.kaldir(FULL, "fen5-su")
    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-su")["arsivlenen_surumler"] == []
    assert ms.find_record(tmp_path, "fen5-su", 1)["status"] == "removed"


def test_gecersiz_durum_arsivi_izinliler_arasinda_sayar(env):
    _, _, yayinci = env
    body = yayinci.katalog(durum="bilinmez")
    assert body["status"] == "gecersiz_durum" and body["izinli"] == ["active", "archived", "removed", "hepsi"]


def test_arsivle_en_yenisi_disindaki_active_surumleri_arsivler(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    for _ in range(3):
        yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    yayinci.yayinla(FULL, taslak_id, slug="fen5-baska")
    _katalogu_yaz(tmp_path, {("fen5-su", 1): "active", ("fen5-su", 2): "active"})
    assert yayinci.katalog(ders="fen")["sayi"] == 4

    body = yayinci.arsivle("isikkurtx@gmail.com", "fen5-su")
    assert body == {"status": "ok", "slug": "fen5-su", "arsivlenen_surum_sayisi": 2, "guncel_surum": 3,
                    "not": "Dosyalar silinmez; eski sürümler archived işaretlenir, adresleri güncel sürüme yönlenir.",
                    "mcp_verified": False}
    for version in (1, 2):
        row = ms.find_record(tmp_path, "fen5-su", version)
        assert row["status"] == "archived" and row["archived_by"] == "isikkurtx@gmail.com" and row["archived_at"]
    assert ms.find_record(tmp_path, "fen5-su", 3)["status"] == "active"
    assert ms.find_record(tmp_path, "fen5-baska", 1)["status"] == "active"
    # İkinci çağrı: arşivlenecek eski sürüm yok, sayı 0.
    again = yayinci.arsivle(FULL, "fen5-su")
    assert again["status"] == "ok" and again["arsivlenen_surum_sayisi"] == 0 and again["guncel_surum"] == 3


def test_arsivle_reddeder_ve_hatayi_kapatir(env, monkeypatch):
    tmp_path, derleyici, yayinci = env
    assert yayinci.arsivle(FULL, "../x") == {"status": "gecersiz_slug", "slug": "../x", "mcp_verified": False}
    assert yayinci.arsivle(FULL, "fen5-yok") == {"status": "bulunamadi", "slug": "fen5-yok", "mcp_verified": False}
    yayinci.yayinla(FULL, _taslak(derleyici), slug="fen5-su")
    yayinci.kaldir(FULL, "fen5-su")
    assert yayinci.arsivle(FULL, "fen5-su")["status"] == "bulunamadi"

    def boom(*args, **kwargs):
        raise RuntimeError("iç ayrıntı")

    monkeypatch.setattr(ms, "read_catalog_with_status", boom)
    body = yayinci.arsivle(FULL, "fen5-su")
    assert body["status"] == "sunucu_hatasi" and "iç ayrıntı" not in json.dumps(body, ensure_ascii=False)


def test_arsivle_araci_tools_uzerinden_calisir(tmp_path):
    settings = load_settings({}, project_root=tmp_path)
    writer = CatalogWriter(settings.data_dir, clock=lambda: NOW)
    draft = {"meta": {"title": "t", "subject": "Fen Bilimleri", "gradeLevel": "5. Sınıf", "mode": "QUIZ"},
             "gates": {"pass": 18, "warn": 0, "fail": 0}}
    for _ in range(2):
        writer.yayinla(FULL, draft, b"<html></html>", "fen5-su", None)
    _katalogu_yaz(settings.data_dir, {("fen5-su", 1): "active"})
    body = tools.Tools(settings, _Fed()).arsivle(FULL, "fen5-su")
    assert body["status"] == "ok" and body["arsivlenen_surum_sayisi"] == 1 and body["guncel_surum"] == 2


# ── İnceleme turu 1, bulgu 8: okunamayan katalog boş sayılmaz ────────────────────────────────

KATALOG_OKUNAMADI_NOTU = ("Modül kataloğu okunamıyor; hiçbir şey yazılmadı. Katalog onarılana dek yayın, kaldırma ve "
                          "arşivleme yapılmaz; yöneticiye bildir.")


@pytest.mark.parametrize("bozuk", [b'{"surum": 1, "moduller": [{"slug": "fen5-su", "vers', b'{"surum": 1}',
                                   b'{"surum": 1, "moduller": "x"}', b"\xff\xfe bozuk"])
def test_okunamayan_katalogda_yazicilar_hicbir_sey_yazmaz(env, bozuk):
    """Kilit altındaki yazıcılar (`yayinla`, `kaldir`, `arsivle`) okunamayan kataloğu boş katalog sayıp bütün satırları
    ezmez: `katalog_okunamadi` döner, katalog dosyasının baytları ve modül dizini değişmez."""
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    path = ms.catalog_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bozuk)

    def dizin():  # kilidin kendi dosyası (.lock) yazı sayılmaz
        return sorted(p.relative_to(tmp_path).as_posix() for p in ms.modules_root(tmp_path).rglob("*")
                      if p.name != ".lock")

    dizin_once = dizin()

    assert yayinci.yayinla(FULL, taslak_id, slug="fen5-su") == {
        "taslak_id": taslak_id, "status": "katalog_okunamadi", "not": KATALOG_OKUNAMADI_NOTU, "mcp_verified": False}
    assert yayinci.kaldir(FULL, "fen5-su") == {
        "slug": "fen5-su", "status": "katalog_okunamadi", "not": KATALOG_OKUNAMADI_NOTU, "mcp_verified": False}
    assert yayinci.arsivle(FULL, "fen5-su") == {
        "slug": "fen5-su", "status": "katalog_okunamadi", "not": KATALOG_OKUNAMADI_NOTU, "mcp_verified": False}
    assert path.read_bytes() == bozuk
    assert dizin() == dizin_once == ["modules/index.json"]
    assert not (ms.modules_root(tmp_path) / "fen5-su").exists()


def test_katalog_dosyasi_yoksa_yayin_bos_katalogla_baslar(env):
    tmp_path, derleyici, yayinci = env
    assert not ms.catalog_path(tmp_path).exists()
    assert yayinci.kaldir(FULL, "fen5-su")["status"] == "bulunamadi"
    assert yayinci.arsivle(FULL, "fen5-su")["status"] == "bulunamadi"
    body = yayinci.yayinla(FULL, _taslak(derleyici), slug="fen5-su")
    assert body["status"] == "ok" and body["version"] == 1
    assert [r["slug"] for r in ms.read_catalog(tmp_path)] == ["fen5-su"]


def test_catalog_writer_okunamayan_katalogu_kendisi_de_reddeder(tmp_path):
    """Yayinci dışındaki çağıran (araç katmanı, betik) da ham boş listeyle yazamaz."""
    from src.mcp_server.katalog import KatalogOkunamadi
    writer = CatalogWriter(tmp_path, clock=lambda: NOW)
    path = ms.catalog_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"{bozuk")
    draft = {"meta": {"title": "t", "subject": "Fen Bilimleri", "gradeLevel": "5. Sınıf", "mode": "QUIZ"},
             "gates": {"pass": 18, "warn": 0, "fail": 0}}
    for cagri in (lambda: writer.yayinla(FULL, draft, b"<html></html>", "fen5-su", None),
                  lambda: writer.kaldir(FULL, "fen5-su"), lambda: writer.arsivle(FULL, "fen5-su")):
        with pytest.raises(KatalogOkunamadi):
            cagri()
    assert path.read_bytes() == b"{bozuk"
