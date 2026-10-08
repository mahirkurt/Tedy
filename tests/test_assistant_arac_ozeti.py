"""tool_end'in okura gösterilen özeti (Carbon AI Chat araç adımı, spec §5.1)."""
from src.assistant_core import AssistantRuntime, ToolLoopResult
from src.assistant_tools import ToolOutcome, arac_ozeti


def _atif(label):
    return {"id": "S1", "kind": "mufredat", "label": label, "locator": {}, "snippet": "gövde metni", "confidence": 1.0}


def test_basarisiz_arac_tek_cumle():
    assert arac_ozeti("kitap_sayfa", ToolOutcome(ok=False, error="HTTP 500 upstream")) == "Bu kaynağa şu an ulaşılamadı"


def test_ogretmen_notlari_atifsiz_ama_adli():
    assert arac_ozeti("skill_kaynagi", ToolOutcome(ok=True, text="## Kavram yanılgıları…")) == "Öğretmen notlarına bakıldı"


def test_tek_iki_cok_atif_ve_tekrar():
    assert arac_ozeti("kitap_sayfa", ToolOutcome(ok=True, citations=[_atif("Matematik 7 (2. Kitap) · s.57")])) \
        == "Matematik 7 (2. Kitap) · s.57"
    assert arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("A"), _atif("A"), _atif("B")])) == "A · B"
    assert arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("A"), _atif("B"), _atif("C")])) == "A ve 2 kaynak daha"


def test_atifsiz_basari_ve_uzunluk_ve_ham_govde_yok():
    assert arac_ozeti("netlestir", ToolOutcome(ok=True, text='{"soru": "…"}')) == "Tamamlandı"
    uzun = arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("ç" * 300)]))
    assert len(uzun) == 120 and uzun.endswith("…")
    assert "gövde metni" not in arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("Etiket")]))


def test_tool_end_olayi_ozet_tasir(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    runtime = AssistantRuntime(tmp_path)

    def sahte_dispatch(name, args, **kwargs):
        if name == "kitap_sayfa":
            return ToolOutcome(ok=True, text="sayfa", citations=[_atif("Fen Bilimleri 7 · s.12")])
        return ToolOutcome(ok=False, error="zaman aşımı")

    def dongu(*, dispatch, **kwargs):
        dispatch("kitap_sayfa", {"sayfa": 12})
        dispatch("mufredat_ara", {"q": "hücre"})
        return ToolLoopResult(text="cevap", citations=[])

    monkeypatch.setattr(runtime.registry, "declarations", lambda *a, **k: [])
    monkeypatch.setattr(runtime.registry, "degraded", lambda: [])
    monkeypatch.setattr(runtime.registry, "dispatch", sahte_dispatch)
    monkeypatch.setattr(runtime.llm, "chat_with_tools", dongu)

    bitenler = [e for e in runtime.chat_events(messages=[{"role": "user", "content": "hücre"}], session_id="s")
                if e["event"] == "tool_end"]
    assert bitenler == [
        {"event": "tool_end", "name": "kitap_sayfa", "ok": True, "ozet": "Fen Bilimleri 7 · s.12"},
        {"event": "tool_end", "name": "mufredat_ara", "ok": False, "ozet": "Bu kaynağa şu an ulaşılamadı"},
    ]
