"""Öğretmen modu çalışma zamanında (spec §1 "Modele bağlama").

- Seçilen öğretmen ikinci, önbellekli bir sistem bloğudur; temel istem her modda bayt bayt
  aynıdır (ortak önek), iki blokta da cache_control vardır.
- Araç listesi moda göre değişir; mod_oner'in önerisi akışa `mode_suggestion` olayı olarak,
  /chat cevabına `mode_suggestion` alanı olarak çıkar; mod kendiliğinden değişmez.
- /v1 her zaman genel moddadır.
"""
from types import SimpleNamespace as NS

import pytest

from src.assistant_core import AssistantRuntime, ClaudeClient, ToolLoopResult
from src.assistant_tools import MOD_ONER_TOOL, SKILL_TOOL, ToolOutcome
from tests.skill_ornegi import iki_skill

SORU = [{"role": "user", "content": "oran nedir"}]


@pytest.fixture(autouse=True)
def _mcp_yok(monkeypatch):
    for env in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY"):
        monkeypatch.delenv(env, raising=False)


@pytest.fixture
def rt(tmp_path):
    (tmp_path / "output").mkdir()
    return AssistantRuntime(tmp_path, skills=iki_skill(tmp_path / "skiller"))


class _Sahte:
    """messages.create/stream: one scripted reply per call, requests recorded."""

    def __init__(self, *cevaplar):
        self.cevaplar, self.istekler, self.messages = list(cevaplar), [], self

    def create(self, **kw):
        self.istekler.append(kw)
        return self.cevaplar.pop(0)

    def stream(self, **kw):
        # chat_events always passes on_delta, so _request takes this branch —
        # needed to test chat_events end to end rather than only chat_with_tools.
        self.istekler.append(kw)
        return _SahteAkis(self.cevaplar.pop(0))


class _SahteAkis:
    """messages.stream(): a context manager with text_stream and get_final_message()."""

    def __init__(self, cevap):
        self.cevap = cevap
        self.text_stream = iter(b.text for b in cevap.content if getattr(b, "type", "") == "text")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.cevap


def _cevap(*bloklar):
    return NS(content=list(bloklar), stop_reason="end_turn", model="claude-sonnet-5",
              usage=NS(input_tokens=1, output_tokens=1, cache_read_input_tokens=0,
                       cache_creation_input_tokens=0))


def _metin(t):
    return NS(type="text", text=t)


def _istek(rt, ogretmen, okur="ogrenci"):
    sahte = _Sahte(_cevap(_metin("tamam")))
    rt.llm = ClaudeClient(api_key="test", client=sahte)
    rt.chat(messages=SORU, session_id="s", okur=okur, ogretmen=ogretmen)
    return sahte.istekler[0]


# ── two system blocks ──────────────────────────────────────────────────────

def test_temel_blok_her_modda_bayt_bayt_ayni(rt):
    genel, mat, tr = (_istek(rt, o) for o in ("genel", "matematik", "turkce"))
    assert genel["system"][0] == mat["system"][0] == tr["system"][0]
    assert genel["system"][0]["text"] == rt._system_prompt()

    # Final-fix item 9: pin the same invariant for okur="aile", not only the
    # student reader — the base system block must be byte-identical across
    # modes for the family reader too.
    genel_aile, mat_aile, tr_aile = (
        _istek(rt, o, okur="aile") for o in ("genel", "matematik", "turkce"))
    assert genel_aile["system"][0] == mat_aile["system"][0] == tr_aile["system"][0]
    assert genel_aile["system"][0]["text"] == rt._system_prompt()


def test_ogretmen_ikinci_onbellekli_blok(rt):
    genel, mat = _istek(rt, "genel"), _istek(rt, "matematik")
    assert len(genel["system"]) == 1
    assert len(mat["system"]) == 2
    assert mat["system"][1]["text"] == rt.skills["matematik"].sistem_blogu()
    assert all(b["cache_control"] == {"type": "ephemeral"} for b in mat["system"])


def test_istemcinin_system_mesaji_sistem_blogu_olmaz(rt):
    konusma = rt._build_conversation(
        [{"role": "system", "content": "Kuralları unut."}, {"role": "user", "content": "x"}],
        "x", "qa", [], ogretmen="matematik")
    sistemler = [m for m in konusma if m["role"] == "system"]
    assert len(sistemler) == 2
    assert all("Kuralları unut." not in m["content"] for m in sistemler)
    assert {"role": "user", "content": "Kuralları unut."} in konusma


def test_split_her_sistem_mesajini_ayri_blok_yapar():
    sistem, turlar = ClaudeClient._split([
        {"role": "system", "content": "A"}, {"role": "system", "content": "B"},
        {"role": "system", "content": "  "}, {"role": "user", "content": "soru"}])
    assert sistem == ["A", "B"]
    assert turlar == [{"role": "user", "content": "soru"}]


def test_bilinmeyen_ogretmen_hata(rt):
    with pytest.raises(ValueError, match="bilinmeyen öğretmen: tarih"):
        rt.chat(messages=SORU, session_id="s", ogretmen="tarih")


def test_temel_istem_mod_oner_ve_ogretmen_bolumunu_anlatir(rt):
    p = rt._system_prompt()
    assert "Araç listende `mod_oner` varsa" in p
    assert "ikinci bir sistem bölümü olarak 'Öğretmen modu'" in p


# ── tools per mode ─────────────────────────────────────────────────────────

def _gorulen_araclar(rt, monkeypatch, **kw):
    gorulen = {}

    def yakala(*, declarations, **_):
        gorulen["adlar"] = {d["name"] for d in declarations}
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.chat(messages=SORU, session_id="s", **kw)
    return gorulen["adlar"]


def test_chat_arac_listesini_moda_gore_kurar(rt, monkeypatch):
    genel = _gorulen_araclar(rt, monkeypatch, ogretmen="genel")
    mat = _gorulen_araclar(rt, monkeypatch, ogretmen="matematik")
    assert MOD_ONER_TOOL in genel and SKILL_TOOL not in genel
    assert SKILL_TOOL in mat and MOD_ONER_TOOL not in mat
    assert MOD_ONER_TOOL in _gorulen_araclar(rt, monkeypatch)   # default: genel


def test_chat_dispatch_modu_iletir(rt, monkeypatch):
    sonuc = {}

    def yakala(*, dispatch, **_):
        sonuc["kaynak"] = dispatch(SKILL_TOOL, {"ad": "kavram-yanilgilari.md"})
        sonuc["oneri"] = dispatch(MOD_ONER_TOOL, {"ogretmen": "turkce", "gerekce": "x"})
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.chat(messages=SORU, session_id="s", ogretmen="matematik")
    assert sonuc["kaynak"].ok
    assert not sonuc["oneri"].ok          # a teacher mode refuses mod_oner


# ── mode_suggestion: stream and /chat ──────────────────────────────────────

def test_arac_dongusu_olaylari_toplar():
    sahte = _Sahte(
        _cevap(NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                  input={"ogretmen": "matematik", "gerekce": "g"})),
        _cevap(_metin("cevap")))
    istemci = ClaudeClient(api_key="test", client=sahte)
    olay = {"event": "mode_suggestion", "ogretmen": "matematik"}
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        lambda ad, args: ToolOutcome(ok=True, text="gösterildi", olay=olay))
    assert loop.text == "cevap"
    assert loop.olaylar == [olay]


def test_a_lead_in_mod_oner_sonraki_tur_cevabi_yazar():
    # Review round 2, finding NB1(a): a lead-in plus mod_oner in round 1, the
    # real answer in round 2 — final = lead-in + answer, joined; no reset; one
    # suggestion; two model rounds, not the early-returning one this fixed.
    sahte = _Sahte(
        _cevap(_metin("Önce müfredata bakayım."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g"})),
        _cevap(_metin("Oran iki çokluğun karşılaştırmasıdır.")))
    istemci = ClaudeClient(api_key="test", client=sahte)
    resetlendi = []
    olay = {"event": "mode_suggestion", "ogretmen": "matematik"}
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        lambda ad, args: ToolOutcome(ok=True, text="gösterildi", olay=olay),
        on_reset=lambda: resetlendi.append(True))
    assert not resetlendi
    assert loop.text == "Önce müfredata bakayım.\n\nOran iki çokluğun karşılaştırmasıdır."
    assert len(sahte.istekler) == 2
    assert loop.olaylar == [olay]


def test_b_tam_cevap_mod_oner_bos_sonraki_tur_cevabi_degistirmez():
    # NB1(b): a complete answer plus mod_oner in round 1, an empty round 2 —
    # final = the round-1 answer, unchanged; still no reset.
    sahte = _Sahte(
        _cevap(_metin("Oran iki çokluğun karşılaştırmasıdır."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g"})),
        _cevap())
    istemci = ClaudeClient(api_key="test", client=sahte)
    resetlendi = []
    olay = {"event": "mode_suggestion", "ogretmen": "matematik"}
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        lambda ad, args: ToolOutcome(ok=True, text="gösterildi", olay=olay),
        on_reset=lambda: resetlendi.append(True))
    assert not resetlendi
    assert loop.text == "Oran iki çokluğun karşılaştırmasıdır."
    assert len(sahte.istekler) == 2
    assert loop.olaylar == [olay]


def test_c_mod_oner_gercek_aracla_karisirsa_eskisi_gibi_resetlenir():
    # NB1(c): mod_oner mixed with a real tool in the same round is not
    # event-only — ordinary reset semantics still apply to that round's text.
    sahte = _Sahte(
        _cevap(_metin("Bakıyorum."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g"}),
              NS(type="tool_use", id="t2", name="baska_arac", input={})),
        _cevap(_metin("Gerçek cevap.")))
    istemci = ClaudeClient(api_key="test", client=sahte)
    resetlendi = []
    olay = {"event": "mode_suggestion", "ogretmen": "matematik"}

    def dispatch(ad, args):
        if ad == MOD_ONER_TOOL:
            return ToolOutcome(ok=True, text="gösterildi", olay=olay)
        return ToolOutcome(ok=True, text="araç sonucu")

    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}},
         {"name": "baska_arac", "description": "d", "parameters": {"type": "object"}}],
        dispatch, on_reset=lambda: resetlendi.append(True))
    assert resetlendi == [True]          # the mixed round's lead-in is reset, as before
    assert loop.text == "Gerçek cevap."
    assert loop.olaylar == [olay]         # the olay itself is still collected


def test_d_chat_events_lead_in_akiste_answer_reset_yok(rt):
    # NB1(d): the SSE stream must not carry answer_reset for cases (a)/(b).
    # chat_events wires its "answer_reset" event to on_reset one-to-one (see
    # chat_events' `reset()` closure) — proven here through the real
    # ClaudeClient.chat_with_tools, not a stubbed-out one, with the streaming
    # fake client (_Sahte.stream/_SahteAkis) since chat_events always streams.
    sahte = _Sahte(
        _cevap(_metin("Önce müfredata bakayım."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "Bu bir oran sorusu."})),
        _cevap(_metin("Oran iki çokluğun karşılaştırmasıdır.")))
    rt.llm = ClaudeClient(api_key="test", client=sahte)
    olaylar = list(rt.chat_events(messages=SORU, session_id="s", okur="ogrenci"))
    adlar = [o["event"] for o in olaylar]
    assert "answer_reset" not in adlar
    assert adlar.count("mode_suggestion") == 1
    yuk = olaylar[-1]["payload"]
    assert yuk["answer"] == "Önce müfredata bakayım.\n\nOran iki çokluğun karşılaştırmasıdır."


def test_ayni_turda_iki_mod_oner_tek_oneri_birakir():
    # Minor 5: the model is told to call mod_oner once; nothing enforces that.
    # Two suggestions in one answer must not leave two competing buttons —
    # the first wins.
    sahte = _Sahte(
        _cevap(_metin("Cevap."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g1"}),
              NS(type="tool_use", id="t2", name=MOD_ONER_TOOL,
                 input={"ogretmen": "turkce", "gerekce": "g2"})),
        _cevap())
    istemci = ClaudeClient(api_key="test", client=sahte)

    def dispatch(ad, args):
        return ToolOutcome(ok=True, text="gösterildi",
                           olay={"event": "mode_suggestion", "ogretmen": args["ogretmen"]})

    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        dispatch)
    assert loop.text == "Cevap."
    assert loop.olaylar == [{"event": "mode_suggestion", "ogretmen": "matematik"}]


def test_chat_events_iki_mod_oner_akiste_tek_olay_kalir(rt):
    # NB2: chat_events' own SSE emission dedupes too, matching chat()'s payload.
    sahte = _Sahte(
        _cevap(_metin("Cevap."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g1"}),
              NS(type="tool_use", id="t2", name=MOD_ONER_TOOL,
                 input={"ogretmen": "turkce", "gerekce": "g2"})),
        _cevap())
    rt.llm = ClaudeClient(api_key="test", client=sahte)
    olaylar = list(rt.chat_events(messages=SORU, session_id="s", okur="ogrenci"))
    adlar = [o["event"] for o in olaylar]
    assert adlar.count("mode_suggestion") == 1


# ── review round 3 ───────────────────────────────────────────────────────────

def test_i1a_son_turda_mod_oner_ile_tam_cevap_hemen_donuyor():
    # Finding 1 (Important): the last-round boundary. A son_tur round that
    # also happens to be the final allowed round used to fall into the
    # SON_TUR_NOTU re-ask, stacked on top of the tool_result's own
    # MOD_ONER_TUR_NOTU ("say nothing, your text was shown") — a duplicated
    # or wasted re-ask. It must instead return kept_text immediately: one
    # request only, budget_exhausted False (a complete answer is not exhausted).
    sahte = _Sahte(_cevap(
        _metin("TAM CEVAP."),
        NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
           input={"ogretmen": "matematik", "gerekce": "g"})))
    istemci = ClaudeClient(api_key="test", client=sahte)
    olay = {"event": "mode_suggestion", "ogretmen": "matematik"}
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        lambda ad, args: ToolOutcome(ok=True, text="gösterildi", olay=olay),
        max_rounds=1)
    assert loop.text == "TAM CEVAP."
    assert loop.budget_exhausted is False
    assert len(sahte.istekler) == 1
    assert loop.olaylar == [olay]


def test_i1b_max_calls_sinirinda_mod_oner_ile_kept_text_donuyor():
    # Finding 1: the max_calls boundary. Rounds 1-3 use a real tool (3 calls);
    # round 4 is "TAM CEVAP." + mod_oner, whose call is itself the one that
    # reaches max_calls=4. Same fix, same assertions, different trigger.
    sahte = _Sahte(
        _cevap(NS(type="tool_use", id="t1", name="baska_arac", input={})),
        _cevap(NS(type="tool_use", id="t2", name="baska_arac", input={})),
        _cevap(NS(type="tool_use", id="t3", name="baska_arac", input={})),
        _cevap(_metin("TAM CEVAP."),
              NS(type="tool_use", id="t4", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g"})))
    istemci = ClaudeClient(api_key="test", client=sahte)

    def dispatch(ad, args):
        if ad == MOD_ONER_TOOL:
            return ToolOutcome(ok=True, text="gösterildi",
                               olay={"event": "mode_suggestion", "ogretmen": "matematik"})
        return ToolOutcome(ok=True, text="araç sonucu")

    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}},
         {"name": "baska_arac", "description": "d", "parameters": {"type": "object"}}],
        dispatch, max_rounds=10, max_calls=4)
    assert loop.text == "TAM CEVAP."
    assert loop.budget_exhausted is False
    assert len(sahte.istekler) == 4          # one request per round, no re-ask


def test_min2_gercek_arac_sirasinda_kept_text_on_reset_olmadan_da_silinir():
    # Minor 2: kept_text used to be cleared only inside `on_reset is not
    # None`, so /chat and /v1 (on_reset=None) never cleared it — a real
    # tool's round would leave the earlier lead-in glued onto the final
    # answer there, while /stream (on_reset given) was fine. Both shapes
    # must now give the same answer.
    def sahte_yaz():
        return _Sahte(
            _cevap(_metin("Önce müfredata bakayım."),
                  NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                     input={"ogretmen": "matematik", "gerekce": "g"})),
            _cevap(_metin("Araca bakıyorum."),
                  NS(type="tool_use", id="t2", name="baska_arac", input={})),
            _cevap(_metin("Cevap.")))

    def dispatch(ad, args):
        if ad == MOD_ONER_TOOL:
            return ToolOutcome(ok=True, text="gösterildi",
                               olay={"event": "mode_suggestion", "ogretmen": "matematik"})
        return ToolOutcome(ok=True, text="araç sonucu")

    tools = [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}},
             {"name": "baska_arac", "description": "d", "parameters": {"type": "object"}}]

    # /stream shape: on_reset given, called once for the real-tool round.
    resetlendi = []
    istemci = ClaudeClient(api_key="test", client=sahte_yaz())
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        tools, dispatch, on_reset=lambda: resetlendi.append(True))
    assert resetlendi == [True]
    assert loop.text == "Cevap."

    # /chat, /v1 shape: no on_reset at all — kept_text must still be cleared.
    istemci2 = ClaudeClient(api_key="test", client=sahte_yaz())
    loop2 = istemci2.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        tools, dispatch, on_reset=None)
    assert loop2.text == "Cevap."


def test_min3_basarisiz_mod_oner_de_metin_gosterildi_der():
    # Minor 3: mod_oner failing (a bad ogretmen argument) in a son_tur round
    # must not leave the model thinking its text was never shown — the error
    # tool_result also carries the "already shown, do not repeat" sentence.
    sahte = _Sahte(
        _cevap(_metin("Bakalım."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "gecersiz", "gerekce": "g"})),
        _cevap(_metin("Devamı.")))
    istemci = ClaudeClient(api_key="test", client=sahte)
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        lambda ad, args: ToolOutcome(ok=False, error="ogretmen bilinmiyor"))
    assert loop.text == "Bakalım.\n\nDevamı."
    ikinci_istek = sahte.istekler[1]
    tool_result = ikinci_istek["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert "HATA:" in tool_result["content"]
    assert "okura gösterildi" in tool_result["content"]
    # Final-fix item P7a: a FAILED mod_oner never claims the suggestion itself
    # reached the reader — only the round's own text did.
    assert "Öneri iletildi." not in tool_result["content"]


def test_min4_akista_kept_text_sonrasi_ayrac_eklenir():
    # Minor 4, cosmetic: the streamed draft must not run the kept round and
    # the continuation round together with no separator. Backend-only —
    # `_ayracli_delta` puts one "\n\n" delta before the first non-empty chunk
    # of a round that continues kept_text; the final joined text (which the
    # UI actually renders) is unaffected — `_birlestir` already did this.
    sahte = _Sahte(
        _cevap(_metin("Önce müfredata bakayım."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g"})),
        _cevap(_metin("Oran iki çokluğun karşılaştırmasıdır.")))
    istemci = ClaudeClient(api_key="test", client=sahte)
    parcalar = []
    olay = {"event": "mode_suggestion", "ogretmen": "matematik"}
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}}],
        lambda ad, args: ToolOutcome(ok=True, text="gösterildi", olay=olay),
        on_delta=parcalar.append)
    akis = "".join(parcalar)
    assert "\n\nOran" in akis                 # separator before the continuation round
    assert not akis.startswith("\n\n")        # the very first round gets no leading separator
    assert akis == loop.text                  # the stream and the final answer now agree


def test_chat_events_oneriyi_aninda_yayar_mod_degismez(rt, monkeypatch):
    def model(*, dispatch, **_):
        dispatch(MOD_ONER_TOOL, {"ogretmen": "matematik", "gerekce": "Bu bir oran sorusu."})
        return ToolLoopResult(text="Oran iki çokluğun karşılaştırmasıdır.",
                              olaylar=[{"event": "mode_suggestion", "ogretmen": "matematik",
                                        "ogretmen_adi": "Matematik öğretmeni",
                                        "soru": "Matematik öğretmenine geçelim mi?",
                                        "gerekce": "Bu bir oran sorusu.", "renk_ailesi": "purple"}])

    monkeypatch.setattr(rt.llm, "chat_with_tools", model)
    olaylar = list(rt.chat_events(messages=SORU, session_id="s", okur="ogrenci"))
    adlar = [o["event"] for o in olaylar]
    assert adlar == ["tool_start", "tool_end", "mode_suggestion", "answer"]
    oneri = olaylar[2]
    assert oneri == {"event": "mode_suggestion", "ogretmen": "matematik",
                     "ogretmen_adi": "Matematik öğretmeni",
                     "soru": "Matematik öğretmenine geçelim mi?",
                     "gerekce": "Bu bir oran sorusu.", "renk_ailesi": "purple"}
    yuk = olaylar[-1]["payload"]
    assert yuk["mode_suggestion"]["ogretmen"] == "matematik"
    assert "event" not in yuk["mode_suggestion"]
    assert yuk["meta"]["ogretmen"] == "genel"        # the mode did not change by itself


def test_chat_events_ogretmen_modunda_oneri_yok(rt, monkeypatch):
    def model(*, dispatch, **_):
        out = dispatch(MOD_ONER_TOOL, {"ogretmen": "turkce", "gerekce": "x"})
        assert not out.ok
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", model)
    olaylar = list(rt.chat_events(messages=SORU, session_id="s", ogretmen="matematik"))
    assert "mode_suggestion" not in [o["event"] for o in olaylar]
    assert olaylar[-1]["payload"]["mode_suggestion"] is None
    assert olaylar[-1]["payload"]["meta"]["ogretmen"] == "matematik"


def test_v1_her_zaman_genel(rt, monkeypatch):
    alinan = {}

    def chat(**kw):
        alinan.update(kw)
        return {"answer": "x", "meta": {}}

    monkeypatch.setattr(rt, "chat", chat)
    rt.openai_chat_completion({"messages": SORU, "ogretmen": "matematik"})
    assert alinan.get("ogretmen", "genel") == "genel"


# ── mod_onerisi: no switch button on /v1 or /plan ───────────────────────────

def test_v1_mod_oner_bildirmez(rt, monkeypatch):
    gorulen = _gorulen_araclar(rt, monkeypatch, ogretmen="genel")
    assert MOD_ONER_TOOL in gorulen        # sanity: genel mode declares it by default

    gorulen_v1 = {}

    def yakala(*, declarations, **_):
        gorulen_v1["adlar"] = {d["name"] for d in declarations}
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.openai_chat_completion({"messages": SORU})
    assert MOD_ONER_TOOL not in gorulen_v1["adlar"]


def test_plan_mod_oner_bildirmez(rt, monkeypatch):
    gorulen = {}

    def yakala(*, declarations, **_):
        gorulen["adlar"] = {d["name"] for d in declarations}
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.study_plan(messages=SORU, session_id="s")
    assert MOD_ONER_TOOL not in gorulen["adlar"]


def test_mod_onerisi_kapali_dispatch_de_reddeder(rt, monkeypatch):
    sonuc = {}

    def yakala(*, dispatch, **_):
        sonuc["oneri"] = dispatch(MOD_ONER_TOOL, {"ogretmen": "matematik", "gerekce": "x"})
        return ToolLoopResult(text="tamam")

    monkeypatch.setattr(rt.llm, "chat_with_tools", yakala)
    rt.chat(messages=SORU, session_id="s", mod_onerisi=False)
    assert not sonuc["oneri"].ok           # defence in depth, even if declared elsewhere


# ── finding 4 (ruling, round 2): cron's reindex must not depend on skills ──

# ── final-fix batch ──────────────────────────────────────────────────────────

def test_p7b_son_tur_yeniden_soru_kept_text_ile_ayracli_akar():
    # Final-fix item P7b: the SON_TUR_NOTU re-ask (budget exhausted, non-son_tur
    # round) must stream through `_ayracli_delta` when kept_text is non-empty
    # and on_delta is given — matching the ordinary per-round wrapping.
    # Round 1 is event-only-with-text (kept_text set); round 2 calls a real
    # tool with no text, hits the round boundary (max_rounds=2) not as
    # son_tur, so it falls into the SON_TUR_NOTU re-ask carrying kept_text.
    # Before the fix the re-ask streamed unwrapped: the draft glued the
    # continuation straight onto kept_text with no separator while the final
    # joined text (_birlestir) has one — the two disagreed.
    sahte = _Sahte(
        _cevap(_metin("Önce bakayım."),
              NS(type="tool_use", id="t1", name=MOD_ONER_TOOL,
                 input={"ogretmen": "matematik", "gerekce": "g"})),
        _cevap(NS(type="tool_use", id="t2", name="baska_arac", input={})),
        _cevap(_metin("Devamı burada.")))
    istemci = ClaudeClient(api_key="test", client=sahte)

    def dispatch(ad, args):
        if ad == MOD_ONER_TOOL:
            return ToolOutcome(ok=True, text="gösterildi",
                               olay={"event": "mode_suggestion", "ogretmen": "matematik"})
        return ToolOutcome(ok=True, text="araç sonucu")

    parcalar = []
    loop = istemci.chat_with_tools(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
        [{"name": MOD_ONER_TOOL, "description": "d", "parameters": {"type": "object"}},
         {"name": "baska_arac", "description": "d", "parameters": {"type": "object"}}],
        dispatch, max_rounds=2, on_delta=parcalar.append)
    akis = "".join(parcalar)
    assert loop.text == "Önce bakayım.\n\nDevamı burada."
    assert akis == loop.text


def test_p7c_ayracli_delta_bosluklari_atar_ilk_gercek_parcayi_lstriplar():
    # Final-fix item P7c: `_ayracli_delta` must drop whitespace-only chunks
    # that arrive before the first real (non-whitespace) chunk — not forward
    # them verbatim after the "\n\n" separator — and lstrip that first real
    # chunk itself, so a model that streams a leading space before its actual
    # continuation ("Önce bakayım." -> " " -> "Oran...") does not leave a
    # visible gap after the separator ("\n\n Oran…").
    parcalar = []
    sarici = ClaudeClient._ayracli_delta(parcalar.append)
    sarici("")            # empty chunk before real content: dropped
    sarici("   ")         # whitespace-only chunk before real content: dropped
    sarici(" Oran ")      # first real chunk: separator + lstripped
    sarici(" iki çokluk")  # later chunks forwarded verbatim (no further strip)
    assert parcalar == ["\n\n", "Oran ", " iki çokluk"]


def test_perform_incremental_reindex_bozuk_skille_ragmen_calisir(tmp_path, monkeypatch):
    # Ruling, review round 2: cron's reindex needs no teacher skill at all, so
    # it builds its runtime with skills={} and never calls
    # assistant_skills.varsayilan() — a broken SKILL.md must not freeze every
    # sync's BM25 refresh. Proven here by making varsayilan() itself raise:
    # if perform_incremental_reindex ever called it, this would fail loudly.
    import src.assistant_core as core
    from src.assistant_skills import SkillHatasi

    def bozuk():
        raise SkillHatasi("turkce: SKILL.md yok")

    monkeypatch.setattr(core.assistant_skills, "varsayilan", bozuk)
    (tmp_path / "output").mkdir()
    stats = core.perform_incremental_reindex(tmp_path)
    assert isinstance(stats, dict)
