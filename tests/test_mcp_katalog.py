"""Catalog writer and publish tools: immutable versions, EXAM/FAIL refusal, soft removal, concurrency."""
import hashlib
from concurrent.futures import ThreadPoolExecutor

import anyio
import pytest

from src import module_store as ms
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
                    "url": f"https://tedy.online/moduller/{SLUG}/v1", "mcp_verified": False}
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
    assert len([r for r in ms.read_catalog(tmp_path) if r["slug"] == "fen5-su"]) == 8


def test_katalog_and_soft_removal(env):
    tmp_path, derleyici, yayinci = env
    taslak_id = _taslak(derleyici)
    yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    yayinci.yayinla(FULL, taslak_id, slug="fen5-su")
    listed = yayinci.katalog(ders="fen", sinif="5")
    assert listed["status"] == "ok" and listed["sayi"] == 2 and listed["mcp_verified"] is False
    assert set(listed["moduller"][0]) == {"slug", "version", "status", "title", "subject", "gradeLevel", "mode",
                                          "outcomes", "ted_link", "gates", "created_at", "url"}
    assert yayinci.katalog(ders="matematik")["sayi"] == 0
    assert yayinci.katalog(durum="bilinmez")["status"] == "gecersiz_durum"
    removed = yayinci.kaldir(FULL, "fen5-su")
    assert removed["status"] == "ok" and removed["kaldirilan_surum_sayisi"] == 2
    assert yayinci.katalog()["sayi"] == 0 and yayinci.katalog(durum="removed")["sayi"] == 2
    assert ms.module_html_path(tmp_path, "fen5-su", 1).is_file()
    row = ms.find_record(tmp_path, "fen5-su", 1)
    assert row["removed_by"] == FULL and row["removed_at"]
    assert yayinci.kaldir(FULL, "fen5-su")["status"] == "bulunamadi"
    assert yayinci.kaldir(FULL, "../x")["status"] == "gecersiz_slug"


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
