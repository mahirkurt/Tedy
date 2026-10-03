"""Sohbet deposu (spec §3). Ağ yok."""
import threading
from datetime import datetime, timezone

import pytest

from src.assistant_sohbet import SohbetDeposu

ISIK = "student@example.test"
SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)


def test_wal_ve_bos_liste(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    assert depo.journal_mode() == "wal"
    assert depo.liste(ISIK) == []


def test_son_yirmi_yeniyi_tutar(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(25):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)
    son = depo.son_mesajlar(sid, 20)
    assert [m["icerik"] for m in son] == [f"m{i}" for i in range(5, 25)]
    assert depo.tum_mesajlar(sid)[0]["icerik"] == "m0"


def test_ayni_saniye_soru_cevap_sirasi(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "matematik", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "matematik", [], SIMDI)
    depo.mesaj_ekle(sid, "assistant", "cevap", "matematik", [], SIMDI)
    assert [m["rol"] for m in depo.son_mesajlar(sid, 20)] == ["user", "assistant"]
    assert [m["rol"] for m in depo.tum_mesajlar(sid)] == ["user", "assistant"]


def test_mesaj_ogretmeni_satiri_ezmez(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "matematik", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "fen", [], SIMDI)
    assert depo.getir(sid)["ogretmen"] == "matematik"
    assert depo.tum_mesajlar(sid)[0]["ogretmen"] == "fen"


def test_iki_yazici(tmp_path):
    yol = tmp_path / "assistant_sohbetler.sqlite"
    depo = SohbetDeposu(yol)
    sid = depo.yarat(ISIK, "genel", SIMDI)
    bariyer = threading.Barrier(2)
    hatalar = []

    def yaz(on):
        try:
            bariyer.wait()
            yerel = SohbetDeposu(yol)
            for i in range(20):
                yerel.mesaj_ekle(sid, "user", f"{on}-{i}", "genel", [], SIMDI)
        except Exception as exc:  # noqa: BLE001 — the assertion is the message
            hatalar.append(exc)

    iplikler = [threading.Thread(target=yaz, args=(n,)) for n in ("a", "b")]
    for t in iplikler:
        t.start()
    for t in iplikler:
        t.join()
    assert hatalar == []
    assert len(SohbetDeposu(yol).tum_mesajlar(sid)) == 40


def test_istek_tekrari_ayni_mesaji_dondurur(tmp_path):
    depo = SohbetDeposu(tmp_path / "sohbet.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    first = depo.mesaj_ekle(sid, "user", "aynı soru", "genel", [], SIMDI, istek_id="once")
    assert depo.mesaj_ekle(sid, "user", "aynı soru", "genel", [], SIMDI, istek_id="once") == first
    depo.mesaj_ekle(sid, "user", "aynı soru", "genel", [], SIMDI, istek_id="intentional-repeat")
    assert len(depo.tum_mesajlar(sid)) == 2


def test_yirmi_asimi_ozeti_yazar_mesaji_silmez(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(21):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)
    gorulen = {}

    def tamamla(prompt):
        gorulen["prompt"] = prompt
        return "kısa özet"

    from src.assistant_core import eski_turleri_ozetle
    eski_turleri_ozetle(depo, sid, tamamla)
    assert depo.ozet_oku(sid) == "kısa özet"
    assert len(depo.tum_mesajlar(sid)) == 21
    assert "user: m0" in gorulen["prompt"]
    assert "user: m20" not in gorulen["prompt"]


def test_yirmi_asmazsa_ozet_yok(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(20):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)

    def tamamla(prompt):
        raise AssertionError("çağrılmamalı")

    from src.assistant_core import eski_turleri_ozetle
    eski_turleri_ozetle(depo, sid, tamamla)
    assert depo.ozet_oku(sid) is None


def test_ozet_hatasi_cevap_satirini_birakir(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(22):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)

    def tamamla(prompt):
        raise RuntimeError("ağ yok")

    from src.assistant_core import eski_turleri_ozetle
    eski_turleri_ozetle(depo, sid, tamamla)
    assert depo.ozet_oku(sid) is None
    assert len(depo.tum_mesajlar(sid)) == 22


def test_private_uploads_and_chat_storage_are_not_indexed(tmp_path):
    from src.assistant_core import AssistantConfig, AssistantIndexer
    output = tmp_path / "output"
    uploads = output / "assistant_uploads" / "synthetic-owner"
    uploads.mkdir(parents=True)
    (uploads / "sample.json").write_text('{"private": "private upload"}')
    (output / "assistant_sohbetler.sqlite").write_text("private chat")
    (output / "lesson.txt").write_text("public lesson")
    config = AssistantConfig.from_project_root(tmp_path)
    files = AssistantIndexer(config)._discover_files()
    assert files == [output / "lesson.txt"]


def test_last_twenty_window_keeps_attachment_only_inside_it(tmp_path):
    from src.assistant_core import AssistantRuntime
    rt = AssistantRuntime(tmp_path)
    messages = [{"role": "user", "content": f"turn{i}"} for i in range(21)]
    attachment = {"meta": {"id": "ab" * 16, "ad": "note.txt", "tur": "txt"}, "veri": b"source"}
    messages[0]["ek_govde"] = [attachment]
    assert not any(isinstance(m["content"], list) for m in rt._build_conversation(
        messages, "turn20", "qa", [], pencere=20))
    messages[1]["ek_govde"] = [attachment]
    assert any(isinstance(m["content"], list) for m in rt._build_conversation(
        messages, "turn20", "qa", [], pencere=20))
    assert not any(isinstance(m["content"], list) for m in rt._build_conversation(
        messages, "turn20", "qa", []))


@pytest.mark.parametrize("metin", ["İlaç kullanıyor", "Boşanma konuşuldu", "05321112233", "veli@example.test"])
def test_sensitive_memory_never_writes(tmp_path, metin):
    from src.assistant_sohbet import hassas_not
    assert hassas_not(metin)
    depo = SohbetDeposu(tmp_path / "sohbet.sqlite")
    assert depo.not_yaz(metin, None, SIMDI) == ""
    nid = depo.not_yaz("Paydada zorlanıyor", None, SIMDI)
    assert not depo.not_duzelt(nid, metin)
    assert depo.notlar()[0]["metin"] == "Paydada zorlanıyor"


@pytest.mark.parametrize("metin", ["Paydada zorlanıyor", "Üçüncü soruyu yarım bırakıyor", "sınav notu düşük", "tanım örneği"])
def test_educational_memory_is_allowed(tmp_path, metin):
    from src.assistant_sohbet import hassas_not
    assert not hassas_not(metin)
    depo = SohbetDeposu(tmp_path / "sohbet.sqlite")
    assert depo.not_yaz(metin, None, SIMDI)


def test_summary_and_notes_live_only_in_wrapper(tmp_path):
    from src.assistant_core import AssistantRuntime, _parcayi_ele
    runtime = AssistantRuntime(tmp_path)
    messages = [{"role": "user", "content": "Payda"}]
    ordinary = runtime._build_conversation(messages, "Payda", "qa", [])
    enriched = runtime._build_conversation(messages, "Payda", "qa", [], pencere=20,
        ozet="Eski soru", notlar=[{"metin": "Örnekle öğreniyor"}])
    assert enriched[0] == ordinary[0]
    assert enriched[-1]["content"].startswith("Önceki özet:\nEski soru")
    assert "Öğrenci notları:\n- Örnekle öğreniyor" in enriched[-1]["content"]
    assert "Öğrenci notları:" not in ordinary[-1]["content"]
    assert _parcayi_ele({"Payda eşittir."}, "Payda eşittir.\n\nYeni satır") == "Yeni satır"
    assert _parcayi_ele({"Payda eşittir."}, "Payda eşittir.") == "Aynı parça zaten duruyor."


def test_upload_binding_keeps_original_chat(tmp_path):
    from src.assistant_uploads import EkDeposu
    from src.module_ticket import email_hash
    import json
    uploads = EkDeposu(tmp_path)
    upload = uploads.kaydet(ISIK, "note.txt", "txt", 1, b"x", SIMDI)
    uploads.bagla(ISIK, upload["id"], "ab" * 16)
    uploads.bagla(ISIK, upload["id"], "cd" * 16)
    assert uploads.oku(ISIK, upload["id"])[0]["bagli_sohbet"] == "ab" * 16
    raw = json.loads((tmp_path / "assistant_uploads" / email_hash(ISIK) / (upload["id"] + ".json")).read_text())
    assert "id" not in raw


def test_visible_card_migration_preserves_existing_message(tmp_path):
    import sqlite3
    from src.assistant_sohbet import SohbetDeposu
    path = tmp_path / "older.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE mesaj (id TEXT PRIMARY KEY, sohbet_id TEXT, rol TEXT, icerik TEXT, "
                 "atiflar_json TEXT DEFAULT '[]', ekler_json TEXT DEFAULT '[]', meta_json TEXT DEFAULT '{}', "
                 "ogretmen TEXT, zaman TEXT, sira INTEGER, istek_id TEXT)")
    conn.execute("INSERT INTO mesaj (id,sohbet_id,rol,icerik,ogretmen,zaman,sira) "
                 "VALUES ('m','s','assistant','eski','genel','2026-10-03T00:00:00Z',1)")
    conn.commit(); conn.close()
    for _ in range(2):
        row = SohbetDeposu(path).tum_mesajlar("s")[0]
        assert row["icerik"] == "eski" and row["kartlar_json"] == "{}"
        assert row["meta_json"] == "{}"


def test_visible_cards_drop_nested_metadata_and_cannot_be_user_injected(tmp_path):
    from src.assistant_sohbet import gorunen_kartlar
    aday = {"ders": "Matematik", "baslik": "Kesirler", "teslim": "", "aciklama": "Sayfa 3",
            "eksik": ["teslim", "private_trace"], "private_trace": "gizli"}
    payload = {"odev_onerisi": {"ek_id": "ab" * 16, "adaylar": [aday], "meta": {"secret": "gizli"}},
               "meta": {"secret": "gizli"}, "tool_results": ["gizli"]}
    temiz = gorunen_kartlar(payload)
    assert "gizli" not in str(temiz) and "private_trace" not in str(temiz)
    depo = SohbetDeposu(tmp_path / "chat.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    depo.mesaj_ekle(sid, "user", "Oku", "genel", [], SIMDI, kartlar=payload)
    assert depo.tum_mesajlar(sid)[0]["kartlar_json"] == "{}"
