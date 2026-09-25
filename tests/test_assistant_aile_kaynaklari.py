"""Görev 5 — aile_kaynak_ara: content/pedagoji as a separate, family-only BM25 section.

content/pedagoji holds adult-facing parenting/learning-science notes (Woolfolk,
Santrock, Child Psychopathology and the household's own pedagogy notes) — 65% of
the assistant's main BM25 index before Görev 1 excluded it from that index. Görev 5
gives the directory its own index directory (same retriever/indexer classes, a
different AssistantConfig) and its own tool, gated by READER, not by whether the
source happens to be wired: only a family member (`okur == "aile"`) ever sees or
can use `aile_kaynak_ara`. Işık (`ogrenci`) and an unknown caller (`bilinmiyor`)
never see it declared, and dispatch() refuses it even if a model calls it anyway
(defence in depth).

Fixtures hold only invented content — never real personal data or real book text.
"""
import sys

import os

os.environ["TEST_AUTH_BYPASS"] = "1"

from src.assistant_core import AssistantRuntime, ToolLoopResult  # noqa: E402
from src.assistant_tools import AILE_TOOL, build_registry  # noqa: E402


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _reg(**kw):
    return build_registry(lambda q, k: [], **kw)


def _rt(tmp_path):
    (tmp_path / "output").mkdir()
    return AssistantRuntime(tmp_path)


# ── declarations(): reader-gated, not source-gated ──────────────────────────

def test_kaynak_verilmemisse_hicbir_okura_ilan_edilmez():
    reg = _reg()  # aile_kaynak_arama never wired
    for okur in ("aile", "ogrenci", "bilinmiyor"):
        assert AILE_TOOL not in {d["name"] for d in reg.declarations(okur)}


def test_kaynak_varken_yalniz_aile_okuruna_ilan_edilir():
    reg = _reg(aile_kaynak_arama=lambda q, k: [])
    assert AILE_TOOL in {d["name"] for d in reg.declarations("aile")}
    assert AILE_TOOL not in {d["name"] for d in reg.declarations("ogrenci")}
    assert AILE_TOOL not in {d["name"] for d in reg.declarations("bilinmiyor")}
    assert AILE_TOOL not in {d["name"] for d in reg.declarations()}  # default: bilinmiyor


def test_arac_parametre_bicimi_sorgu_ister():
    reg = _reg(aile_kaynak_arama=lambda q, k: [])
    decl = next(d for d in reg.declarations("aile") if d["name"] == AILE_TOOL)
    assert decl["parameters"]["required"] == ["sorgu"]
    assert "sorgu" in decl["parameters"]["properties"]


# ── dispatch(): refused for anyone but "aile", even if called anyway ────────

ROWS = [{"path": "content/pedagoji/05-ebeveyn-rehberligi.md", "chunk_index": 0,
         "text": "Sınav kaygısı olan bir çocukla konuşurken sakin bir ton kullanın.",
         "snippet": "Sınav kaygısı olan bir çocukla konuşurken sakin bir ton.",
         "confidence": 0.87}]


def test_dispatch_ogrenci_ve_bilinmiyor_icin_reddedilir():
    reg = _reg(aile_kaynak_arama=lambda q, k: ROWS)
    for okur in ("ogrenci", "bilinmiyor"):
        out = reg.dispatch(AILE_TOOL, {"sorgu": "sınav kaygısı"}, okur=okur)
        assert not out.ok
        assert "aile" in out.error
    varsayilan = reg.dispatch(AILE_TOOL, {"sorgu": "sınav kaygısı"})  # default okur
    assert not varsayilan.ok


def test_dispatch_aile_icin_sonuc_doner_dogru_kind_ve_okunur_etiketle():
    reg = _reg(aile_kaynak_arama=lambda q, k: ROWS)
    out = reg.dispatch(AILE_TOOL, {"sorgu": "sınav kaygısı"}, okur="aile")
    assert out.ok
    assert "Sınav kaygısı" in out.text
    atif = out.citations[0]
    assert atif["kind"] == "aile-kaynak"
    assert atif["label"] == "Aile kaynağı · Ebeveyn Rehberligi"
    assert "content/pedagoji" not in atif["label"]  # no internal path in the label


def test_kaynak_okunamazsa_modele_hata_olarak_gider():
    def patlak(q, k):
        raise OSError("disk")
    reg = _reg(aile_kaynak_arama=patlak)
    out = reg.dispatch(AILE_TOOL, {"sorgu": "x"}, okur="aile")
    assert not out.ok and "aile kaynağı araması hatası" in out.error


def test_kaynak_hic_baglanmadiysa_aile_icin_bile_bilinmeyen_arac():
    reg = _reg()  # source never wired at all
    out = reg.dispatch(AILE_TOOL, {"sorgu": "x"}, okur="aile")
    assert not out.ok and "bilinmeyen araç" in out.error


# ── system prompt: routes family questions to it, forbids it for Işık ───────

def test_sistem_istemi_araci_taniyip_isiga_yasaklar(tmp_path):
    p = _rt(tmp_path)._system_prompt()
    assert "aile_kaynak_ara" in p
    assert "Işık'la konuşurken bu araçtan hiç söz etme" in p


# ── chat(): declarations and dispatch both carry okur end to end ────────────

def test_chat_arac_listesi_yalniz_aile_okurunda_gorunur(tmp_path, monkeypatch):
    rt = _rt(tmp_path)
    gorulen = {}

    def yakala(*, declarations, **kwargs):
        gorulen["adlar"] = {d["name"] for d in declarations}
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)

    rt.chat(messages=[{"role": "user", "content": "sınav kaygısı"}], session_id="s", okur="ogrenci")
    assert AILE_TOOL not in gorulen["adlar"]

    rt.chat(messages=[{"role": "user", "content": "sınav kaygısı"}], session_id="s", okur="aile")
    assert AILE_TOOL in gorulen["adlar"]


def test_chat_dispatch_okuru_iletir_ogrenci_cagirsa_bile_reddeder(tmp_path, monkeypatch):
    rt = _rt(tmp_path)
    yakalanan = {}

    def yakala(*, dispatch, **kwargs):
        # A model that ignored the (undeclared) tool list and called it anyway.
        yakalanan["cikti"] = dispatch(AILE_TOOL, {"sorgu": "x"})
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.chat(messages=[{"role": "user", "content": "x"}], session_id="s", okur="ogrenci")
    assert not yakalanan["cikti"].ok


# ── chat_events(): the streaming path threads okur too (Fix round 1, Minor 2) ──
# chat_events() builds its own dispatch wrapper (`real_dispatch`) from the
# kwargs it receives, separately from chat()'s own default-partial path — a
# fix to one does not exercise the other, so both need their own coverage.

def test_chat_events_arac_listesi_yalniz_aile_okurunda_gorunur(tmp_path, monkeypatch):
    rt = _rt(tmp_path)
    gorulen = {}

    def yakala(*, declarations, **kwargs):
        gorulen["adlar"] = {d["name"] for d in declarations}
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)

    list(rt.chat_events(messages=[{"role": "user", "content": "sınav kaygısı"}],
                        session_id="s", okur="ogrenci"))
    assert AILE_TOOL not in gorulen["adlar"]

    list(rt.chat_events(messages=[{"role": "user", "content": "sınav kaygısı"}],
                        session_id="s", okur="aile"))
    assert AILE_TOOL in gorulen["adlar"]


def test_chat_events_dispatch_okuru_iletir_ogrenci_cagirsa_bile_reddeder(tmp_path, monkeypatch):
    rt = _rt(tmp_path)
    yakalanan = {}

    def yakala(*, dispatch, **kwargs):
        # A model that ignored the (undeclared) tool list and called it anyway.
        yakalanan["cikti"] = dispatch(AILE_TOOL, {"sorgu": "x"})
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    list(rt.chat_events(messages=[{"role": "user", "content": "x"}], session_id="s", okur="ogrenci"))
    assert not yakalanan["cikti"].ok


def test_chat_events_dispatch_aile_okuru_icin_izin_verir(tmp_path, monkeypatch):
    rt = _rt(tmp_path)
    yakalanan = {}

    def yakala(*, dispatch, **kwargs):
        yakalanan["cikti"] = dispatch(AILE_TOOL, {"sorgu": "x"})
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    list(rt.chat_events(messages=[{"role": "user", "content": "x"}], session_id="s", okur="aile"))
    assert yakalanan["cikti"].ok


# ── real files: the family index is separate, own directory, reported by reindex ──

def test_reindex_ayri_dizine_yazar_ve_pedagojiyi_ana_indeksten_ayik_tutar(tmp_path):
    _write(tmp_path, "content/pedagoji/05-ebeveyn-rehberligi.md",
           "Sinavkaygisibenzersizanahtar hakkinda bir not: sakin kalin.")
    _write(tmp_path, "output/notlar.txt", "gerçek okul verisi, tamamen farklı bir konu")
    rt = AssistantRuntime(tmp_path)

    stats = rt.reindex()

    assert (tmp_path / "output" / "assistant_index" / "chunks.json").exists()
    assert (tmp_path / "output" / "assistant_index_aile" / "chunks.json").exists()
    assert stats["aile_kaynagi"]["files_indexed"] == 1

    # The distinctive keyword lives only under content/pedagoji: the family
    # retriever finds it, the main index (which excludes that directory
    # outright) never does.
    aile_isabet = rt._aile_search("sinavkaygisibenzersizanahtar", 8)
    assert aile_isabet and "content/pedagoji" in aile_isabet[0]["path"]

    ana_isabet = rt._local_search("sinavkaygisibenzersizanahtar", 8)
    assert ana_isabet == []


def test_aile_indeksleyici_pedagojiyi_bulur_ana_indeksleyici_bulmaz(tmp_path):
    _write(tmp_path, "content/pedagoji/01-gelisim-psikolojisi.md", "içerik")
    rt = _rt(tmp_path)

    aile_bulunan = {p.relative_to(tmp_path).as_posix() for p in rt.aile_indexer._discover_files()}
    ana_bulunan = {p.relative_to(tmp_path).as_posix() for p in rt.indexer._discover_files()}

    assert "content/pedagoji/01-gelisim-psikolojisi.md" in aile_bulunan
    assert "content/pedagoji/01-gelisim-psikolojisi.md" not in ana_bulunan


def test_reindex_cli_ozeti_iki_indeksi_de_raporlar(tmp_path, monkeypatch, capsys):
    _write(tmp_path, "content/pedagoji/01-gelisim-psikolojisi.md", "içerik")

    import src.reindex_assistant as cli
    monkeypatch.setattr(sys, "argv", ["reindex_assistant.py"])
    monkeypatch.setattr(cli, "PROJECT_ROOT", str(tmp_path))

    cli.main()

    out = capsys.readouterr().out
    assert "[Assistant] Reindex complete" in out
    assert "[Assistant] Aile kaynağı reindex complete" in out


def test_reindex_cli_dusen_dosyalari_hem_ana_hem_aile_icin_yazdirir(tmp_path, monkeypatch, capsys):
    """Fix round 1, Minor 3: "sessiz düşme yok" (task-1 brief §2) applies to
    the CLI summary too — a file the chunk cap dropped must be named, for
    both indexes, not only counted."""
    monkeypatch.setenv("ASSISTANT_MAX_CHUNKS", "1")
    _write(tmp_path, "output/aaa_ilk.txt", "kısa metin bir")
    _write(tmp_path, "output/zzz_ikinci.txt", "kısa metin iki")
    _write(tmp_path, "content/pedagoji/01-ilk.md", "kısa metin uc")
    _write(tmp_path, "content/pedagoji/02-ikinci.md", "kısa metin dort")

    import src.reindex_assistant as cli
    monkeypatch.setattr(sys, "argv", ["reindex_assistant.py"])
    monkeypatch.setattr(cli, "PROJECT_ROOT", str(tmp_path))

    cli.main()

    out = capsys.readouterr().out
    assert out.count("dusen_dosyalar") == 2  # once per index's own summary
    assert "output/zzz_ikinci.txt" in out
    assert "content/pedagoji/02-ikinci.md" in out
