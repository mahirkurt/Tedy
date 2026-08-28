# TEDY Asistanı — Müfredat Temellendirmesi ve Cevap Arayüzü (Faz 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Asistanın konu bilgisini ham EBA OCR'ından MEB müfredat korpusuna taşımak, modeli araç çağıran bir döngüye almak ve cevap yüzeyini Carbon AI token sistemiyle yeniden kurmak.

**Architecture:** Flask backend'e bağımlılıksız bir MCP HTTP istemcisi eklenir. Gemini, `tools/list`'ten üretilen fonksiyon tanımlarıyla ≤4 turluk bir döngüde çalışır; Işık'ın kendi verisi için yerel BM25 retriever, konu bilgisi için iki MCP sunucusu araç olarak sunulur. Yanıttaki `[S1]` işaretleri backend'de gerçek kaynaklara çözülür, çözülmeyenler düşer; frontend işaretleri silmek yerine tıklanabilir çipe çevirir.

**Tech Stack:** Python 3.9+ / Flask / gunicorn / `requests` (yeni bağımlılık yok) · `google-genai` · React 19 / `@carbon/react` 1.102 / `@carbon/themes` 11.69 / Vite / pytest / Playwright

**Spec:** [docs/superpowers/specs/2026-08-23-ai-chat-mufredat-temellendirme-design.md](../specs/2026-08-23-ai-chat-mufredat-temellendirme-design.md)

## Global Constraints

- **Yeni Python bağımlılığı yok.** MCP istemcisi `requests` + stdlib ile yazılır. Resmî `mcp` SDK'sı async-öncelikli olduğu için Flask sync worker'larıyla çakışır.
- **Uydurma yasağı.** Kazanım kodu, kitap adı, sayfa numarası yalnız araç çıktısından gelir. Araç sonuç döndürmediyse model eksikliği beyan eder, doldurmaz.
- **Otorite ayrımı.** Işık'ın verisi (ödev/sınav/not/program/duyuru) → yerel korpus. Konu/müfredat/kazanım → MEB MCP. Bir atıf her zaman hangi sınıftan geldiğini taşır.
- **Sessiz arıza yok.** Her degradasyon `meta.degraded` dizisine yazılır ve kullanıcıya rozetle gösterilir.
- **Araç açıklamaları birebir korunur.** MCP `inputSchema`'daki `description` alanları Gemini'ye değiştirilmeden geçirilir — kanonik biçimi (`grade: "5.Sınıf"`) modele öğreten şey odur.
- **Dal:** `feat/assistant-mufredat-grounding`. Her task kendi commit'ini atar.
- **Dal bağımlılığı — Task 8 öncesi ZORUNLU.** Carbon `--cds-*` köprüsü düzeltmesi
  (`bf86329 fix: make the Carbon token bridge actually bridge`) **bu dalda değil**,
  `feat/carbon-token-fidelity` dalında. `:root`'a `@include theme.theme(themes.$g10)`
  gömen o commit olmadan `--cds-ai-*` token'ları `:root` altında çözülmez ve
  Task 8–10'un tamamı sessizce fallback renklere düşer. Task 8'e başlamadan önce:
  `git merge feat/carbon-token-fidelity`. Task 1–7 (backend) bu bağımlılıktan
  etkilenmez, önce koşabilir.
- **Test komutu:** `python -m pytest tests/<dosya> -v` (repo kökünden). **Otomatik testlerin hiçbiri ağa çıkmaz** — MCP ve Gemini sahte nesnelerle taklit edilir. Canlı doğrulama yalnız elle çalıştırılan "duman testi" adımlarındadır (Task 2 Adım 5, Task 6 Adım 5); bunlar CI'da koşmaz.
- **Çalışma ağacı uyarısı:** `ted-theme.scss`, `CalendarEvents.tsx`, `DashboardHeader.tsx`, `GradeTable.tsx`, `TodaySchedule.tsx` üzerinde kullanıcının commit edilmemiş değişiklikleri var. **`git add .` veya `git commit -a` KULLANMA** — her commit'te yalnız o task'ın dosyalarını açıkça stage et.

---

## Dosya Yapısı

**Oluşturulacak**

| Dosya | Sorumluluk |
|---|---|
| `src/mcp_client.py` | Tek bir MCP sunucusuna Streamable-HTTP konuşan istemci. Oturum yaşam döngüsü, SSE + düz JSON ayrıştırma, yeniden deneme. Başka hiçbir şey bilmez. |
| `src/assistant_tools.py` | MCP + yerel araçları tek bir kayıt defterinde toplar; şema sanitizasyonu, beyaz liste, çağrı yönlendirme. Gemini'yi bilmez, yalnız düz dict üretir. |
| `dashboard/src/components/AssistantChat.scss` | Sohbet yüzeyinin tüm stilleri, Carbon AI token'larıyla. |
| `dashboard/src/components/CitationChip.tsx` | `[S1]` çipi + Carbon AI popover'ı. |
| `dashboard/src/components/SourcePanel.tsx` | `kind`'a göre gruplanmış kaynak paneli. |
| `tests/test_assistant_models.py` | Model zinciri ve 404 davranışı. |
| `tests/test_mcp_client.py` | İstemci protokol davranışı (sahte session ile, ağsız). |
| `tests/test_assistant_tools.py` | Şema sanitizasyonu ve yönlendirme. |
| `tests/test_assistant_citations.py` | Atıf çözümü ve orphan düşürme. |

**Değiştirilecek**

| Dosya | Değişiklik |
|---|---|
| `src/assistant_core.py` | `GeminiClient` model zinciri + `chat_with_tools()`; `AssistantRuntime.chat()` araç döngüsüne geçer; atıf şeması ve doğrulama; sistem promptu. |
| `src/dashboard_api.py` | `/api/assistant/stream` SSE ucu. |
| `dashboard/src/types.ts` | `AssistantCitation` genişler, `meta` alanları eklenir. |
| `dashboard/src/components/AssistantChat.tsx` | Markdown render, atıf çipleri, mesaj eylemleri, degradasyon rozeti; `stripInlineCitations()` kaldırılır. |
| `dashboard/src/theme/ted-theme.scss` | `.ac*` blokları çıkarılır. |
| `~/.config/systemd/user/ted-dashboard.service` | `--worker-class gthread --threads 4`. |
| `.env` | Ölü `ASSISTANT_*` Ollama değişkenleri silinir. |
| `docs/assistant-go-live.md` | Gemini + MCP gerçeğine göre yeniden yazılır. |

---

## Task 1: Model zincirini onar

Canlı arızayı ilk kapatan task. Bugün `gemini-2.0-flash` ve `gemini-2.0-flash-lite` **404** dönüyor, yani üç basamaklı görünen yedeklilik tek basamak. Bu task tek başına dağıtılabilir ve tek başına değer üretir.

**Files:**
- Modify: `src/assistant_core.py` (`GeminiClient`, ~168-250)
- Modify: `.env` (ölü değişkenler)
- Test: `tests/test_assistant_models.py`

**Interfaces:**
- Consumes: yok (ilk task)
- Produces: `GeminiClient.FAST_MODELS: list[str]`, `GeminiClient.DEEP_MODELS: list[str]`, `GeminiClient.chat(messages, temperature=0.2, tier="fast", max_output_tokens=2048) -> str`, `GeminiClient.last_model_used: str`, `GeminiClient._unavailable: set[str]`

- [ ] **Step 1: Write the failing test**

`tests/test_assistant_models.py` oluştur:

```python
"""GeminiClient model chain behaviour — no network."""
import pytest
from src.assistant_core import GeminiClient


class _FakeModels:
    """Records calls and replays a scripted outcome per model name."""

    def __init__(self, script):
        self.script = script          # {model_name: Exception | str}
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        outcome = self.script.get(model, "ok")
        if isinstance(outcome, Exception):
            raise outcome
        return type("R", (), {"text": outcome})()


class _FakeClient:
    def __init__(self, script):
        self.models = _FakeModels(script)


def _client(script):
    c = GeminiClient(api_key="test-key")
    c._client = _FakeClient(script)
    return c


def test_fast_chain_has_no_retired_models():
    """gemini-2.0-* were measured returning 404 on 2026-08-23."""
    chain = GeminiClient.FAST_MODELS + GeminiClient.DEEP_MODELS
    assert not [m for m in chain if m.startswith("gemini-2.0")]


def test_404_model_is_permanently_disabled_and_chain_continues():
    first = GeminiClient.FAST_MODELS[0]
    err = Exception("404 NOT_FOUND. This model is no longer available.")
    c = _client({first: err})

    assert c.chat([{"role": "user", "content": "selam"}]) == "ok"
    assert first in c._unavailable
    assert c.last_model_used == GeminiClient.FAST_MODELS[1]

    # Second call must not spend a round-trip on the dead model again.
    c._client.models.calls.clear()
    c.chat([{"role": "user", "content": "tekrar"}])
    assert first not in c._client.models.calls


def test_quota_exhaustion_is_temporary_not_permanent():
    first = GeminiClient.FAST_MODELS[0]
    err = Exception("429 RESOURCE_EXHAUSTED quota")
    c = _client({first: err})

    c.chat([{"role": "user", "content": "selam"}])
    assert first in c._exhausted
    assert first not in c._unavailable


def test_deep_tier_prefers_pro_then_falls_back_to_fast():
    c = _client({})
    c.chat([{"role": "user", "content": "plan"}], tier="deep")
    assert c.last_model_used == GeminiClient.DEEP_MODELS[0]

    c2 = _client({GeminiClient.DEEP_MODELS[0]: Exception("429 RESOURCE_EXHAUSTED")})
    c2.chat([{"role": "user", "content": "plan"}], tier="deep")
    assert c2.last_model_used == GeminiClient.FAST_MODELS[0]


def test_output_token_cap_is_passed_through():
    c = _client({})
    captured = {}
    orig = c._client.models.generate_content

    def spy(*, model, contents, config):
        captured.update(config)
        return orig(model=model, contents=contents, config=config)

    c._client.models.generate_content = spy
    c.chat([{"role": "user", "content": "x"}], max_output_tokens=8192)
    assert captured["max_output_tokens"] == 8192
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_assistant_models.py -v`
Expected: FAIL — `AttributeError: type object 'GeminiClient' has no attribute 'FAST_MODELS'`

- [ ] **Step 3: Implement the model chain**

`src/assistant_core.py` içinde `GeminiClient` sınıfının `MODELS` listesini kaldır, yerine:

```python
class GeminiClient:
    """Gemini API chat client — fast cloud inference, no local memory cost."""

    # Measured 2026-08-23 against the live key: every model here answers and
    # supports function calling. gemini-2.0-* were removed because the API now
    # returns 404 "no longer available" for them — the old chain only looked
    # redundant, so the first quota hit took the assistant down entirely.
    FAST_MODELS = [
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-flash-lite-latest",
    ]
    DEEP_MODELS = ["gemini-pro-latest"]

    MODELS = FAST_MODELS  # backwards compatibility for models() endpoint

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self._client: Any = None
        self.last_model_used = ""
        self._exhausted: set[str] = set()   # quota — clears when all are spent
        self._unavailable: set[str] = set()  # 404 — never retried this process
```

`chat()` imzasını ve gövdesini değiştir:

```python
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        tier: str = "fast",
        max_output_tokens: int = 2048,
    ) -> str:
        if not self.available:
            raise RuntimeError("gemini_no_api_key")

        client = self._get_client()
        prompt = self._build_prompt(messages)

        last_error = ""
        for model in self._chain(tier):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    },
                )
                text = (response.text or "").strip()
                if text:
                    self.last_model_used = model
                    return text
                last_error = "empty_gemini_response"
            except Exception as e:
                last_error = self._classify_failure(model, e)

        raise RuntimeError(last_error or "gemini_all_models_failed")

    def _chain(self, tier: str) -> list[str]:
        """Candidate models for a tier, skipping known-dead and spent ones."""
        base = list(self.DEEP_MODELS) + list(self.FAST_MODELS) \
            if tier == "deep" else list(self.FAST_MODELS)
        base = [m for m in base if m not in self._unavailable]
        live = [m for m in base if m not in self._exhausted]
        if live:
            return live
        # Every candidate is quota-spent; the window may have rolled over.
        self._exhausted.clear()
        return base

    def _classify_failure(self, model: str, exc: Exception) -> str:
        err = str(exc)
        if "404" in err or "no longer available" in err:
            # Permanent: the model was retired. Retrying it every request
            # burns a round-trip and hides the real error behind a dead one.
            self._unavailable.add(model)
            logger.error("Gemini model %s is retired (404); disabling", model)
            return f"model_retired:{model}"
        if "RESOURCE_EXHAUSTED" in err or "429" in err:
            self._exhausted.add(model)
            logger.warning("Gemini model %s quota exhausted", model)
            return f"quota_exhausted:{model}"
        logger.error("Gemini error (%s): %s", model, err)
        return err
```

Mevcut prompt kurma kodunu `_build_prompt(messages)` adlı yardımcıya taşı (davranış aynı: `system` rolleri başa toplanır, kalanlar iki satır boşlukla birleşir).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_assistant_models.py -v`
Expected: 5 passed

- [ ] **Step 5: Regresyon — mevcut asistan testleri hâlâ geçiyor mu**

Run: `python -m pytest tests/test_assistant_core.py tests/test_assistant_api.py -v`
Expected: PASS. `MODELS` takma adı `models()` ucunu koruyor; kırılma olursa orada.

- [ ] **Step 6: `.env`'deki ölü değişkenleri sil**

Şu satırlar Gemini yolunda hiç okunmuyor, yanıltıcı; sil:
`ASSISTANT_CHAT_MODEL`, `ASSISTANT_CHAT_FALLBACK_MODEL`, `ASSISTANT_OLLAMA_CHAT_TIMEOUT_SECONDS`, `ASSISTANT_OLLAMA_EMBED_TIMEOUT_SECONDS`, `ASSISTANT_OLLAMA_KEEP_ALIVE`, `ASSISTANT_OLLAMA_CHAT_NUM_PREDICT`

`ASSISTANT_EMBED_MODEL`, `ASSISTANT_ENABLE_EMBEDDINGS`, `OLLAMA_BASE_URL` **kalır** — indeksleme yolu bunları kullanıyor.

- [ ] **Step 7: Commit**

```bash
git add src/assistant_core.py tests/test_assistant_models.py .env
git commit -m "fix: drop retired models from the Gemini fallback chain

Two of the three fallbacks returned 404 'no longer available', so the chain
only looked redundant — the first quota hit took the assistant down. Retired
models are now disabled permanently on 404 and separated from quota
exhaustion, which is temporary and clears when every candidate is spent."
```

---

## Task 2: MCP istemcisi

**Files:**
- Create: `src/mcp_client.py`
- Test: `tests/test_mcp_client.py`

**Interfaces:**
- Consumes: yok
- Produces:
  - `McpToolResult(ok: bool, text: str, images: list[dict], error: str | None)`
  - `McpClient(name: str, url: str, api_key: str, timeout: float = 25.0, session=None)`
  - `McpClient.list_tools() -> list[dict]` — her eleman `{"name": str, "description": str, "inputSchema": dict}`
  - `McpClient.call_tool(name: str, arguments: dict) -> McpToolResult`
  - `McpClient.healthy: bool`

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_client.py` oluştur:

```python
"""MCP client protocol behaviour. No network: a fake session replays responses."""
import json
import pytest
from src.mcp_client import McpClient, McpToolResult


class _Resp:
    def __init__(self, body, headers=None, status=200):
        self._body = body
        self.headers = headers or {"content-type": "application/json"}
        self.status_code = status

    @property
    def text(self):
        return self._body


class _FakeSession:
    """Replays a scripted list of responses and records the requests made."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.requests.append({
            "url": url,
            "headers": dict(headers or {}),
            "body": json.loads(data) if data else None,
        })
        return self.responses.pop(0)


def _init_resp(session_id="sid-1"):
    return _Resp(
        json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "fake", "version": "1"}}}),
        headers={"content-type": "application/json", "mcp-session-id": session_id},
    )


def _client(responses):
    return McpClient(name="fake", url="https://x/mcp", api_key="k",
                     session=_FakeSession(responses))


def test_initialize_sends_bearer_and_captures_session_id():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3,
                          "result": {"tools": [
                              {"name": "t", "description": "d",
                               "inputSchema": {"type": "object"}}]}})),
    ])
    tools = c.list_tools()

    assert [t["name"] for t in tools] == ["t"]
    first = c._session.requests[0]
    assert first["headers"]["Authorization"] == "Bearer k"
    assert first["body"]["method"] == "initialize"
    # Every request after initialize must carry the session id.
    assert c._session.requests[-1]["headers"]["mcp-session-id"] == "sid-1"


def test_sse_framed_response_is_parsed():
    """egitim-kaynak answers in text/event-stream; mufredat in plain JSON."""
    sse = ("event: message\n"
           'data: {"jsonrpc":"2.0","id":3,"result":{"tools":[]}}\n\n')
    c = _client([
        _init_resp(),
        _Resp(sse, headers={"content-type": "text/event-stream"}),
    ])
    assert c.list_tools() == []


def test_list_tools_is_cached_after_first_call():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": {"tools": [
            {"name": "t", "description": "d", "inputSchema": {}}]}})),
    ])
    c.list_tools()
    before = len(c._session.requests)
    c.list_tools()
    assert len(c._session.requests) == before, "schema must not be refetched"


def test_call_tool_extracts_text_and_image_blocks():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": {"content": [
            {"type": "text", "text": "birinci"},
            {"type": "text", "text": "ikinci"},
            {"type": "image", "data": "AAA", "mimeType": "image/png"},
        ]}})),
    ])
    out = c.call_tool("t", {"q": "x"})

    assert out.ok is True
    assert out.text == "birinci\nikinci"
    assert out.images == [{"data": "AAA", "mimeType": "image/png"}]


def test_dropped_session_is_reinitialised_once_then_the_call_retried():
    c = _client([
        _init_resp("sid-1"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "error": {
            "code": -32001, "message": "session not found"}})),
        _init_resp("sid-2"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 4,
                          "result": {"content": [{"type": "text", "text": "ok"}]}})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is True and out.text == "ok"
    assert c._session.requests[-1]["headers"]["mcp-session-id"] == "sid-2"


def test_second_session_failure_gives_up_without_raising():
    c = _client([
        _init_resp("sid-1"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "error": {
            "code": -32001, "message": "session not found"}})),
        _init_resp("sid-2"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 4, "error": {
            "code": -32001, "message": "session not found"}})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is False
    assert "session" in (out.error or "")
    assert c.healthy is False


def test_tool_error_surfaces_as_not_ok_never_raises():
    """A schema rejection must reach the caller as data, so the model can be
    told what it got wrong instead of the request dying."""
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": {
            "isError": True,
            "content": [{"type": "text", "text": "validation error: q required"}]}})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is False
    assert "q required" in (out.error or "")


def test_transport_exception_is_contained():
    class _Boom:
        requests = []

        def post(self, *a, **k):
            raise OSError("connection refused")

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_Boom())
    out = c.call_tool("t", {})

    assert out.ok is False and c.healthy is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mcp_client'`

- [ ] **Step 3: Implement the client**

`src/mcp_client.py` oluştur:

```python
"""Minimal Streamable-HTTP MCP client.

The official `mcp` Python SDK is async-first and would fight Flask's sync
workers, and the protocol surface this project needs is small: initialize,
notifications/initialized, tools/list, tools/call. So this speaks it directly
over `requests` with no new dependency.

Two response encodings are supported because the two servers differ — the
curriculum server answers in plain JSON, the OER server in text/event-stream.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 600


@dataclass
class McpToolResult:
    ok: bool
    text: str = ""
    images: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class McpClient:
    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, name: str, url: str, api_key: str,
                 timeout: float = 25.0, session: Any = None) -> None:
        self.name = name
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self._session = session if session is not None else requests.Session()
        self._sid: str | None = None
        self._sid_at: float = 0.0
        self._tools: list[dict[str, Any]] | None = None
        self._healthy = True
        self._rpc_id = 0

    @property
    def healthy(self) -> bool:
        return self._healthy

    # ── transport ────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self._sid:
            h["mcp-session-id"] = self._sid
        return h

    @staticmethod
    def _decode(resp: Any) -> dict[str, Any]:
        ctype = (resp.headers or {}).get("content-type", "")
        body = resp.text
        if "text/event-stream" in ctype:
            for line in body.splitlines():
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload.startswith("{"):
                        return json.loads(payload)
            raise ValueError("sse_no_data_frame")
        return json.loads(body)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._session.post(
            self.url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        sid = (resp.headers or {}).get("mcp-session-id")
        if sid:
            self._sid = sid
            self._sid_at = time.time()
        if not str(payload.get("method", "")).startswith("notifications/"):
            return self._decode(resp)
        return {}

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    # ── session ──────────────────────────────────────────────────────────

    def _session_expired(self) -> bool:
        return (not self._sid) or (time.time() - self._sid_at > SESSION_TTL_SECONDS)

    def _initialize(self) -> None:
        self._sid = None
        self._post({
            "jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
            "params": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "tedy-assistant", "version": "1.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    @staticmethod
    def _is_session_error(rpc: dict[str, Any]) -> bool:
        err = rpc.get("error") or {}
        return "session" in str(err.get("message", "")).lower()

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """One JSON-RPC round trip, re-initialising once if the session died."""
        for attempt in (1, 2):
            if self._session_expired():
                self._initialize()
            rpc = self._post({
                "jsonrpc": "2.0", "id": self._next_id(),
                "method": method, "params": params,
            })
            if not self._is_session_error(rpc):
                return rpc
            # Server forgot us. Re-initialise and replay — but only once, so a
            # server that always rejects cannot spin here.
            self._sid = None
            if attempt == 2:
                self._healthy = False
                return rpc
        return {}

    # ── public API ───────────────────────────────────────────────────────

    def list_tools(self) -> list[dict[str, Any]]:
        if self._tools is not None:
            return self._tools
        try:
            rpc = self._rpc("tools/list", {})
        except Exception as exc:
            self._healthy = False
            logger.error("MCP %s tools/list failed: %s", self.name, exc)
            return []
        tools = (rpc.get("result") or {}).get("tools")
        if tools is None:
            self._healthy = False
            return []
        self._tools = tools
        self._healthy = True
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolResult:
        try:
            rpc = self._rpc("tools/call",
                            {"name": name, "arguments": arguments})
        except Exception as exc:
            self._healthy = False
            logger.error("MCP %s call %s failed: %s", self.name, name, exc)
            return McpToolResult(ok=False, error=str(exc))

        if rpc.get("error"):
            msg = str(rpc["error"].get("message", "rpc_error"))
            return McpToolResult(ok=False, error=msg)

        result = rpc.get("result") or {}
        texts, images = [], []
        for block in result.get("content") or []:
            if block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif block.get("type") == "image":
                images.append({"data": block.get("data", ""),
                               "mimeType": block.get("mimeType", "image/png")})
        joined = "\n".join(t for t in texts if t)

        if result.get("isError"):
            # Tool-level failure (bad arguments, not found). Data, not an
            # exception: the caller feeds it back to the model to correct.
            return McpToolResult(ok=False, error=joined or "tool_error")

        self._healthy = True
        return McpToolResult(ok=True, text=joined, images=images)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mcp_client.py -v`
Expected: 8 passed

- [ ] **Step 5: Canlı duman testi (elle, bir kez)**

```bash
python -c "
import os
from src.mcp_client import McpClient
c = McpClient('mufredat','https://mufredat.cureonics.com/mcp',os.environ['MUFREDAT_MCP_API_KEY'])
print('araç sayısı:', len(c.list_tools()))
r = c.call_tool('list_textbooks', {'grade':'6'})
print('ok:', r.ok, '| ilk 120:', r.text[:120])
"
```
Expected: `araç sayısı: 21`, `ok: True`

- [ ] **Step 6: Commit**

```bash
git add src/mcp_client.py tests/test_mcp_client.py
git commit -m "feat: add a dependency-free MCP client for the assistant

Speaks Streamable-HTTP directly over requests rather than pulling in the
official SDK, which is async-first and would fight Flask's sync workers. Both
response encodings are handled because the two servers differ, and a dropped
session is re-initialised once before the call is replayed. Tool-level
failures come back as data so the caller can hand them to the model to
correct, instead of killing the request."
```

---

## Task 3: Araç kayıt defteri ve şema sanitizasyonu

**Files:**
- Create: `src/assistant_tools.py`
- Test: `tests/test_assistant_tools.py`

**Interfaces:**
- Consumes: `McpClient`, `McpToolResult` (Task 2)
- Produces:
  - `TOOL_ALLOWLIST: dict[str, tuple[str, str]]` — `{gemini_adı: (sunucu_adı, mcp_araç_adı)}`
  - `sanitize_schema(schema: dict) -> dict`
  - `McpRegistry(clients: dict[str, McpClient], local_search: Callable[[str, int], list[dict]])`
  - `McpRegistry.declarations() -> list[dict]` — `{"name","description","parameters"}`
  - `McpRegistry.dispatch(name: str, args: dict) -> ToolOutcome`
  - `McpRegistry.degraded() -> list[str]`
  - `ToolOutcome(ok: bool, text: str, citations: list[dict], error: str | None)`
  - `build_registry(local_search: Callable[[str, int], list[dict]]) -> McpRegistry`

- [ ] **Step 1: Write the failing test**

`tests/test_assistant_tools.py` oluştur:

```python
"""Tool registry: schema sanitisation, allowlist, dispatch, degradation."""
import pytest
from src.assistant_tools import (
    TOOL_ALLOWLIST, McpRegistry, sanitize_schema,
)
from src.mcp_client import McpToolResult


# The real inputSchema of maarif-mufredat's search_learning_outcomes, verbatim
# as returned by tools/list on 2026-08-23. Pydantic emits anyOf[T, null] for
# optionals and a title on every field.
REAL_SCHEMA = {
    "type": "object",
    "title": "tool_search_learning_outcomesArguments",
    "properties": {
        "q": {"description": "Arama sorgusu (örn. 'kesir', 'türev').",
              "title": "Q", "type": "string"},
        "grade": {"anyOf": [{"type": "string"}, {"type": "null"}],
                  "default": None,
                  "description": "Sınıf filtresi.", "title": "Grade"},
        "limit": {"default": 20, "maximum": 200, "minimum": 1,
                  "title": "Limit", "type": "integer"},
    },
    "required": ["q"],
}


def test_optional_anyof_collapses_to_the_non_null_type():
    out = sanitize_schema(REAL_SCHEMA)
    assert out["properties"]["grade"]["type"] == "string"
    assert "anyOf" not in out["properties"]["grade"]


def test_descriptions_survive_verbatim():
    """Measured: passing the schema WITH descriptions made the model send the
    canonical grade '5.Sınıf'; a hand-written declaration made it send '6'."""
    out = sanitize_schema(REAL_SCHEMA)
    assert out["properties"]["q"]["description"] == \
        "Arama sorgusu (örn. 'kesir', 'türev')."


def test_pydantic_title_noise_is_stripped():
    out = sanitize_schema(REAL_SCHEMA)
    assert "title" not in out
    assert all("title" not in p for p in out["properties"].values())


def test_required_list_is_preserved():
    assert sanitize_schema(REAL_SCHEMA)["required"] == ["q"]


def test_parameterless_tool_yields_empty_properties():
    out = sanitize_schema({"type": "object", "properties": {},
                           "title": "tool_server_infoArguments"})
    assert out["properties"] == {}
    assert out["required"] == []


class _FakeClient:
    def __init__(self, name, tools, result=None, healthy=True):
        self.name = name
        self._tools = tools
        self._result = result or McpToolResult(ok=True, text="sonuç")
        self.healthy = healthy
        self.calls = []

    def list_tools(self):
        return self._tools

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self._result


def _registry(**over):
    tools = [{"name": "search_learning_outcomes",
              "description": "Kazanım araması.", "inputSchema": REAL_SCHEMA}]
    clients = {"maarif-mufredat": _FakeClient("maarif-mufredat", tools)}
    clients.update(over.pop("clients", {}))
    return McpRegistry(clients=clients,
                       local_search=over.pop("local_search", lambda q, k: []))


def test_declarations_expose_only_allowlisted_tools_under_local_names():
    reg = _registry()
    names = {d["name"] for d in reg.declarations()}
    assert "kazanim_ara" in names
    assert "search_learning_outcomes" not in names
    assert names <= set(TOOL_ALLOWLIST) | {"ogrenci_verisi_ara"}


def test_dispatch_maps_local_name_to_the_mcp_tool_name():
    reg = _registry()
    reg.dispatch("kazanim_ara", {"q": "kesir"})
    client = reg.clients["maarif-mufredat"]
    assert client.calls == [("search_learning_outcomes", {"q": "kesir"})]


def test_local_search_tool_returns_student_citations():
    rows = [{"path": "output/scraped_data.json", "snippet": "Ödev: kesirler",
             "chunk_index": 3, "confidence": 0.8}]
    reg = _registry(local_search=lambda q, k: rows)
    out = reg.dispatch("ogrenci_verisi_ara", {"query": "ödev"})

    assert out.ok is True
    assert out.citations[0]["kind"] == "ogrenci"
    assert out.citations[0]["locator"]["path"] == "output/scraped_data.json"


def test_curriculum_dispatch_tags_citations_as_mufredat():
    reg = _registry()
    out = reg.dispatch("kazanim_ara", {"q": "kesir"})
    assert out.citations[0]["kind"] == "mufredat"


def test_unknown_tool_name_is_reported_not_raised():
    out = _registry().dispatch("uydurma_arac", {})
    assert out.ok is False and "uydurma_arac" in (out.error or "")


def test_unhealthy_server_is_reported_as_degraded():
    tools = [{"name": "kb_search", "description": "OER.", "inputSchema": {}}]
    down = _FakeClient("egitim-kaynak", tools, healthy=False)
    reg = _registry(clients={"egitim-kaynak": down})
    assert "egitim-kaynak" in reg.degraded()


def test_tool_error_text_is_passed_back_for_the_model_to_correct():
    tools = [{"name": "search_learning_outcomes", "description": "d",
              "inputSchema": REAL_SCHEMA}]
    bad = _FakeClient("maarif-mufredat", tools,
                      result=McpToolResult(ok=False, error="Field required: q"))
    reg = McpRegistry(clients={"maarif-mufredat": bad}, local_search=lambda q, k: [])
    out = reg.dispatch("kazanim_ara", {})

    assert out.ok is False
    assert "Field required: q" in (out.error or "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_assistant_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.assistant_tools'`

- [ ] **Step 3: Implement the registry**

`src/assistant_tools.py` oluştur:

```python
"""Tool registry for the assistant's function-calling loop.

Declarations are built from each server's own inputSchema rather than written
by hand. That is not a style preference: search_learning_outcomes takes `q`
(not `query`), wants `grade` as a string, and only its description says the
canonical form is "5.Sınıf". Measured — a hand-written declaration produced
grade:"6"; the server's schema, descriptions intact, produced grade:"5.Sınıf".
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from src.mcp_client import McpClient, McpToolResult

logger = logging.getLogger(__name__)

# Gemini-facing name -> (server, MCP tool name).
# Ten of the 27 available tools. The rest are not exposed because a large tool
# list bloats every prompt and slows the loop; adding one is a single line.
TOOL_ALLOWLIST: dict[str, tuple[str, str]] = {
    "kazanim_ara":       ("maarif-mufredat", "search_learning_outcomes"),
    "kazanim_listele":   ("maarif-mufredat", "list_learning_outcomes"),
    "mufredat_ara":      ("maarif-mufredat", "search"),
    "kitap_listele":     ("maarif-mufredat", "list_textbooks"),
    "kitap_sayfa":       ("maarif-mufredat", "get_document_text"),
    "figur_ara":         ("maarif-mufredat", "search_figures"),
    "figur_getir":       ("maarif-mufredat", "get_figure"),
    "oer_ara":           ("egitim-kaynak", "kb_search"),
    "oer_kazanima_gore": ("egitim-kaynak", "kb_for_outcome"),
}

# Which citation class a server's output belongs to. The distinction is load
# bearing: local files are authoritative for Işık's own data, the curriculum
# server for subject knowledge, and the two must never be blended.
_KIND_BY_TOOL: dict[str, str] = {
    "kitap_sayfa": "kitap",
    "figur_ara": "kitap",
    "figur_getir": "kitap",
    "oer_ara": "oer",
    "oer_kazanima_gore": "oer",
}

LOCAL_TOOL = "ogrenci_verisi_ara"

MCP_SERVERS = {
    "maarif-mufredat": ("https://mufredat.cureonics.com/mcp",
                        "MUFREDAT_MCP_API_KEY"),
    "egitim-kaynak": ("https://egitim-kaynak.cureonics.com/mcp",
                      "EGITIM_KAYNAK_MCP_API_KEY"),
}


@dataclass
class ToolOutcome:
    ok: bool
    text: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """MCP inputSchema -> a declaration parameter block.

    The installed google-genai accepts the raw Pydantic schema today, so this
    is a sanitiser rather than a rewriter: it drops `title` noise and collapses
    anyOf[T, null] to T, keeping every description byte-for-byte. Doing it in
    one place also means a future SDK that stops accepting anyOf needs one fix.
    """
    props: dict[str, Any] = {}
    for key, spec in (schema.get("properties") or {}).items():
        if "anyOf" in spec:
            non_null = [a for a in spec["anyOf"] if a.get("type") != "null"]
            base = dict(non_null[0]) if non_null else {"type": "string"}
        else:
            base = {"type": spec.get("type", "string")}
        clean: dict[str, Any] = {"type": base.get("type", "string")}
        if spec.get("description"):
            clean["description"] = spec["description"]
        if spec.get("enum"):
            clean["enum"] = spec["enum"]
        props[key] = clean
    return {
        "type": "object",
        "properties": props,
        "required": list(schema.get("required") or []),
    }


class McpRegistry:
    def __init__(self, clients: dict[str, McpClient],
                 local_search: Callable[[str, int], list[dict[str, Any]]]) -> None:
        self.clients = clients
        self.local_search = local_search

    def degraded(self) -> list[str]:
        return sorted(n for n, c in self.clients.items() if not c.healthy)

    def declarations(self) -> list[dict[str, Any]]:
        decls: list[dict[str, Any]] = [{
            "name": LOCAL_TOOL,
            "description": (
                "Işık'ın kendi okul verisinde arama yapar: ödevler, sınavlar, "
                "notlar, ders programı, duyurular, ders içerikleri. Işık'a özel "
                "her soru için BU aracı kullan — konu/müfredat bilgisi için değil."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {
                    "type": "string",
                    "description": "Aranacak ifade (ör. 'matematik ödevi', 'sınav tarihleri')."}},
                "required": ["query"],
            },
        }]
        for local_name, (server, mcp_name) in TOOL_ALLOWLIST.items():
            client = self.clients.get(server)
            if client is None:
                continue
            spec = next((t for t in client.list_tools()
                         if t.get("name") == mcp_name), None)
            if spec is None:
                logger.warning("MCP %s does not expose %s", server, mcp_name)
                continue
            decls.append({
                "name": local_name,
                "description": spec.get("description", ""),
                "parameters": sanitize_schema(spec.get("inputSchema") or {}),
            })
        return decls

    def dispatch(self, name: str, args: dict[str, Any]) -> ToolOutcome:
        if name == LOCAL_TOOL:
            return self._dispatch_local(args)
        if name not in TOOL_ALLOWLIST:
            return ToolOutcome(ok=False, error=f"bilinmeyen araç: {name}")

        server, mcp_name = TOOL_ALLOWLIST[name]
        client = self.clients.get(server)
        if client is None:
            return ToolOutcome(ok=False, error=f"sunucu yapılandırılmadı: {server}")

        result: McpToolResult = client.call_tool(mcp_name, args)
        if not result.ok:
            return ToolOutcome(ok=False, error=result.error or "araç hatası")

        kind = _KIND_BY_TOOL.get(name, "mufredat")
        return ToolOutcome(
            ok=True,
            text=result.text,
            citations=[{
                "kind": kind,
                "label": self._label(kind, name, args),
                "locator": {"tool": name, "args": args, "server": server},
                "snippet": result.text[:400],
                "confidence": 0.9,
            }],
        )

    def _dispatch_local(self, args: dict[str, Any]) -> ToolOutcome:
        query = str(args.get("query", "")).strip()
        rows = self.local_search(query, 8)
        citations = [{
            "kind": "ogrenci",
            "label": os.path.basename(str(r.get("path", ""))) or "okul verisi",
            "locator": {"path": r.get("path", ""),
                        "chunk_index": r.get("chunk_index", 0)},
            "snippet": str(r.get("snippet", ""))[:400],
            "confidence": float(r.get("confidence", 0.0) or 0.0),
        } for r in rows]
        text = "\n\n".join(str(r.get("snippet", "")) for r in rows) or "(kayıt yok)"
        return ToolOutcome(ok=True, text=text, citations=citations)

    @staticmethod
    def _label(kind: str, tool: str, args: dict[str, Any]) -> str:
        if kind == "kitap":
            doc = args.get("document_id")
            page = args.get("page") or args.get("page_range")
            if doc and page:
                return f"Ders kitabı #{doc} · s.{page}"
            return "Ders kitabı"
        if kind == "oer":
            return "Açık eğitsel kaynak"
        subject = args.get("subject") or args.get("q") or ""
        return f"MEB müfredatı · {subject}" if subject else "MEB müfredatı"


def build_registry(local_search: Callable[[str, int], list[dict[str, Any]]]
                   ) -> McpRegistry:
    """Wire the configured servers. A server with no key is simply absent —
    its tools are not declared and the loop degrades instead of failing."""
    clients: dict[str, McpClient] = {}
    for name, (url, env_key) in MCP_SERVERS.items():
        key = os.environ.get(env_key, "").strip()
        if not key:
            logger.warning("MCP %s disabled: %s not set", name, env_key)
            continue
        clients[name] = McpClient(name=name, url=url, api_key=key)
    return McpRegistry(clients=clients, local_search=local_search)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_assistant_tools.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add src/assistant_tools.py tests/test_assistant_tools.py
git commit -m "feat: build tool declarations from each MCP server's own schema

Hand-written declarations get these wrong in ways that cost model rounds:
search_learning_outcomes takes q rather than query, wants grade as a string,
and only its description carries the canonical '5.Sınıf' form. Passing the
server's schema through with descriptions intact is what makes the model send
the right arguments, so the layer sanitises rather than rewrites.

Ten of twenty-seven tools are exposed; a long tool list bloats every prompt.
Citations carry the class they came from so local files stay authoritative for
Işık's own data and the curriculum server for subject knowledge."
```

---

## Task 4: Araç çağıran döngü

**Files:**
- Modify: `src/assistant_core.py` (`GeminiClient`)
- Test: `tests/test_assistant_models.py` (genişletilir)

**Interfaces:**
- Consumes: `GeminiClient._chain` (Task 1), `McpRegistry.declarations/dispatch` + `ToolOutcome` (Task 3)
- Produces: `GeminiClient.chat_with_tools(messages, declarations, dispatch, tier="fast", max_rounds=4, max_output_tokens=2048) -> ToolLoopResult` ve `ToolLoopResult(text: str, citations: list[dict], tool_calls: list[dict], budget_exhausted: bool)`

- [ ] **Step 1: Write the failing test**

`tests/test_assistant_models.py` sonuna ekle:

```python
from src.assistant_tools import ToolOutcome


class _Part:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


class _FC:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _Cand:
    def __init__(self, parts):
        self.content = type("C", (), {"parts": parts})()


class _ToolResp:
    def __init__(self, parts, text=""):
        self.candidates = [_Cand(parts)]
        self.text = text


class _ScriptedModels:
    """Replays one response per generate_content call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.configs = []

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        return self.responses.pop(0)


def _tool_client(responses):
    c = GeminiClient(api_key="test-key")
    c._client = type("C", (), {"models": _ScriptedModels(responses)})()
    return c


DECLS = [{"name": "kazanim_ara", "description": "d",
          "parameters": {"type": "object", "properties": {}, "required": []}}]


def test_tool_call_is_dispatched_and_its_citations_are_collected():
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="Kesirler [S1] konusuna bak.")],
                  text="Kesirler [S1] konusuna bak."),
    ])
    seen = []

    def dispatch(name, args):
        seen.append((name, args))
        return ToolOutcome(ok=True, text="MAT.5.1.1 kesirler",
                           citations=[{"kind": "mufredat", "label": "MEB",
                                       "locator": {}, "snippet": "s", "confidence": 0.9}])

    out = c.chat_with_tools([{"role": "user", "content": "kesir"}], DECLS, dispatch)

    assert seen == [("kazanim_ara", {"q": "kesir"})]
    assert out.text == "Kesirler [S1] konusuna bak."
    assert len(out.citations) == 1
    assert out.tool_calls[0]["name"] == "kazanim_ara"
    assert out.tool_calls[0]["ok"] is True
    assert out.budget_exhausted is False


def test_a_failing_tool_is_fed_back_so_the_model_can_correct_itself():
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {}))]),
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])
    calls = []

    def dispatch(name, args):
        calls.append(args)
        if not args:
            return ToolOutcome(ok=False, error="Field required: q")
        return ToolOutcome(ok=True, text="sonuç")

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)

    assert calls == [{}, {"q": "kesir"}]
    assert out.text == "bitti"
    assert out.tool_calls[0]["ok"] is False


def test_round_budget_stops_a_model_that_never_stops_calling_tools():
    loop = [_ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "x"}))])
            for _ in range(6)]
    c = _tool_client(loop + [_ToolResp([_Part(text="özet")], text="özet")])

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS,
                            lambda n, a: ToolOutcome(ok=True, text="t"),
                            max_rounds=3)

    assert out.budget_exhausted is True
    assert len(out.tool_calls) == 3


def test_an_answer_with_no_tool_call_returns_immediately():
    c = _tool_client([_ToolResp([_Part(text="selam")], text="selam")])
    out = c.chat_with_tools([{"role": "user", "content": "selam"}], DECLS,
                            lambda n, a: ToolOutcome(ok=True))
    assert out.text == "selam" and out.tool_calls == []


def test_tools_are_actually_offered_to_the_model():
    c = _tool_client([_ToolResp([_Part(text="x")], text="x")])
    c.chat_with_tools([{"role": "user", "content": "q"}], DECLS,
                      lambda n, a: ToolOutcome(ok=True))
    assert "tools" in c._client.models.configs[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_assistant_models.py -v -k tool`
Expected: FAIL — `AttributeError: 'GeminiClient' object has no attribute 'chat_with_tools'`

- [ ] **Step 3: Implement the loop**

`src/assistant_core.py` içinde, `GeminiClient` sınıfına ekle (dosya başına `from dataclasses import dataclass, field` gerekiyorsa ekle):

```python
@dataclass
class ToolLoopResult:
    text: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    budget_exhausted: bool = False
```

`GeminiClient` içine:

```python
    def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        declarations: list[dict[str, Any]],
        dispatch: Any,
        tier: str = "fast",
        max_rounds: int = 4,
        max_output_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> ToolLoopResult:
        """Run the model until it answers, dispatching tools it asks for.

        The round budget is a hard stop: a model that keeps calling tools would
        otherwise hold a worker open indefinitely. When it trips, the model is
        asked once more with tools withdrawn, so the user gets an answer from
        the evidence already gathered instead of an error.
        """
        from google.genai import types

        if not self.available:
            raise RuntimeError("gemini_no_api_key")
        client = self._get_client()

        tools = [types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=d["name"],
                description=d.get("description", ""),
                parameters=d.get("parameters") or {"type": "object", "properties": {}},
            ) for d in declarations])]

        transcript = self._build_prompt(messages)
        out = ToolLoopResult()

        for round_no in range(max_rounds + 1):
            offer_tools = round_no < max_rounds
            config: dict[str, Any] = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }
            if offer_tools:
                config["tools"] = tools

            response = self._generate(client, transcript, config, tier)
            calls = self._function_calls(response)

            if not calls:
                out.text = (getattr(response, "text", "") or "").strip()
                return out

            if not offer_tools:
                # Budget spent and the model still wants tools; the loop above
                # already withdrew them, so this branch cannot recurse.
                out.budget_exhausted = True
                out.text = (getattr(response, "text", "") or "").strip()
                return out

            for call in calls:
                args = dict(call.args or {})
                started = time.perf_counter()
                outcome = dispatch(call.name, args)
                elapsed = int((time.perf_counter() - started) * 1000)
                out.tool_calls.append({
                    "name": call.name, "ms": elapsed, "ok": bool(outcome.ok),
                })
                if outcome.ok:
                    out.citations.extend(outcome.citations)
                    body = outcome.text
                else:
                    # Hand the failure back verbatim. The schemas are strict and
                    # the message names the offending field, so the model can
                    # usually fix its own call on the next round.
                    body = f"HATA: {outcome.error}"
                transcript += (
                    f"\n\n[araç:{call.name} girdi={json.dumps(args, ensure_ascii=False)}]\n"
                    f"{body[:4000]}"
                )
                if len(out.tool_calls) >= max_rounds:
                    break

            if len(out.tool_calls) >= max_rounds:
                out.budget_exhausted = True
                final = self._generate(
                    client, transcript,
                    {"temperature": temperature,
                     "max_output_tokens": max_output_tokens}, tier)
                out.text = (getattr(final, "text", "") or "").strip()
                return out

        return out

    def _generate(self, client: Any, contents: str,
                  config: dict[str, Any], tier: str) -> Any:
        last_error = ""
        for model in self._chain(tier):
            try:
                resp = client.models.generate_content(
                    model=model, contents=contents, config=config)
                self.last_model_used = model
                return resp
            except Exception as e:
                last_error = self._classify_failure(model, e)
        raise RuntimeError(last_error or "gemini_all_models_failed")

    @staticmethod
    def _function_calls(response: Any) -> list[Any]:
        calls = []
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in (getattr(content, "parts", None) or []):
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    calls.append(fc)
        return calls
```

`json` ve `time` zaten import edilmiş durumda; değilse ekle.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_assistant_models.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add src/assistant_core.py tests/test_assistant_models.py
git commit -m "feat: let the assistant reach for sources instead of being handed them

A tool-calling loop replaces the single-shot generation, so the model decides
whether a question needs Işık's own records or the curriculum corpus. Failed
tool calls are fed back verbatim rather than swallowed — the schemas name the
offending field, so the model usually corrects itself on the next round.

The round budget withdraws the tools rather than erroring, so a model that
will not stop calling them still produces an answer from what was gathered."
```

---

## Task 5: Atıf şeması ve doğrulama

**Files:**
- Modify: `src/assistant_core.py` (`AssistantRuntime`)
- Test: `tests/test_assistant_citations.py`

**Interfaces:**
- Consumes: Task 3'ün atıf dict'leri (`kind`/`label`/`locator`/`snippet`/`confidence`)
- Produces: `AssistantRuntime._finalize_citations(text: str, citations: list[dict]) -> tuple[str, list[dict], int]` — `(temizlenmiş_metin, id_atanmış_atıflar, düşürülen_sayısı)`

- [ ] **Step 1: Write the failing test**

`tests/test_assistant_citations.py` oluştur:

```python
"""Citation resolution: markers the model emits must map to real sources."""
import pytest
from src.assistant_core import AssistantRuntime


@pytest.fixture
def runtime(tmp_path):
    (tmp_path / "output").mkdir()
    return AssistantRuntime(tmp_path)


def _cite(kind="mufredat", label="MEB", snippet="s"):
    return {"kind": kind, "label": label, "locator": {},
            "snippet": snippet, "confidence": 0.9}


def test_markers_are_numbered_in_the_order_the_tools_returned(runtime):
    text, cites, dropped = runtime._finalize_citations(
        "Önce [S1] sonra [S2].", [_cite(label="A"), _cite(label="B")])

    assert [c["id"] for c in cites] == ["S1", "S2"]
    assert [c["label"] for c in cites] == ["A", "B"]
    assert dropped == 0
    assert text == "Önce [S1] sonra [S2]."


def test_a_marker_with_no_source_behind_it_is_removed(runtime):
    """The old code deleted every marker in the frontend, so a correct citation
    could never reach the reader. Now only unresolvable ones go."""
    text, cites, dropped = runtime._finalize_citations(
        "Gerçek [S1] ama uydurma [S7].", [_cite()])

    assert "[S7]" not in text
    assert "[S1]" in text
    assert dropped == 1


def test_uncited_sources_are_dropped_from_the_panel(runtime):
    """A source the answer never refers to is noise in the sidebar."""
    _, cites, _ = runtime._finalize_citations("Yalnız [S1].",
                                              [_cite(label="A"), _cite(label="B")])
    assert [c["label"] for c in cites] == ["A"]


def test_repeated_marker_keeps_one_source_entry(runtime):
    _, cites, dropped = runtime._finalize_citations("[S1] ve yine [S1].", [_cite()])
    assert len(cites) == 1 and dropped == 0


def test_answer_without_markers_keeps_no_sources(runtime):
    text, cites, dropped = runtime._finalize_citations("Atıfsız cevap.", [_cite()])
    assert text == "Atıfsız cevap." and cites == [] and dropped == 0


def test_removing_a_marker_does_not_leave_double_spaces(runtime):
    text, _, _ = runtime._finalize_citations("Bir [S9] iki.", [])
    assert text == "Bir iki."


def test_every_surviving_citation_carries_its_kind(runtime):
    _, cites, _ = runtime._finalize_citations(
        "[S1] [S2]", [_cite(kind="ogrenci"), _cite(kind="kitap")])
    assert [c["kind"] for c in cites] == ["ogrenci", "kitap"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_assistant_citations.py -v`
Expected: FAIL — `AttributeError: 'AssistantRuntime' object has no attribute '_finalize_citations'`

- [ ] **Step 3: Implement resolution**

`AssistantRuntime` içine ekle:

```python
    _MARKER_RE = re.compile(r"\[S(\d+)\]")

    def _finalize_citations(
        self,
        text: str,
        citations: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]], int]:
        """Resolve the model's [S1] markers against the sources tools returned.

        Markers are assigned in tool-return order. A marker pointing at nothing
        is removed from the prose and counted, rather than left to imply
        evidence that does not exist — and rather than being stripped wholesale
        in the frontend, which is what previously severed text from sources.
        """
        indexed = {i: dict(c) for i, c in enumerate(citations, start=1)}
        for i, c in indexed.items():
            c["id"] = f"S{i}"

        used: list[int] = []
        dropped = 0

        def replace(match: "re.Match[str]") -> str:
            nonlocal dropped
            n = int(match.group(1))
            if n in indexed:
                if n not in used:
                    used.append(n)
                return match.group(0)
            dropped += 1
            return ""

        cleaned = self._MARKER_RE.sub(replace, text)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r" +([,.;:!?])", r"\1", cleaned).strip()

        return cleaned, [indexed[n] for n in used], dropped
```

`re` modülü dosyanın başında import edilmiş olmalı; değilse ekle.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_assistant_citations.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/assistant_core.py tests/test_assistant_citations.py
git commit -m "feat: resolve the model's citation markers against real sources

The prompt asked for [S1] markers and the frontend deleted them with a regex,
so a correct citation could never reach the reader. Markers are now resolved
in the backend: ones that point at a real source survive and become the
sidebar's contents, ones that point at nothing are removed from the prose and
counted, and sources the answer never cites do not clutter the panel."
```

---

## Task 6: Çalışma zamanını bağla

**Files:**
- Modify: `src/assistant_core.py` (`AssistantRuntime.__init__`, `chat`, `study_plan`)
- Test: `tests/test_assistant_core.py` (genişletilir)

**Interfaces:**
- Consumes: Task 3 `build_registry`, Task 4 `chat_with_tools`, Task 5 `_finalize_citations`
- Produces: `AssistantRuntime.chat()` yanıt zarfı — `meta` içinde `tier`, `tool_calls`, `dropped_citations`, `degraded`, `budget_exhausted`

- [ ] **Step 1: Write the failing test**

`tests/test_assistant_core.py` sonuna ekle:

```python
from src.assistant_core import AssistantRuntime, ToolLoopResult


DEEP_INTENTS = ("study_plan", "grade_analysis", "exam_solving")


def test_deep_tier_is_chosen_by_intent_not_by_the_model():
    """Tier selection is deterministic so cost and latency stay predictable."""
    for intent in DEEP_INTENTS:
        assert AssistantRuntime._tier_for(intent, force_deep=False) == "deep"
    assert AssistantRuntime._tier_for("qa", force_deep=False) == "fast"


def test_explicit_user_request_forces_the_deep_tier():
    assert AssistantRuntime._tier_for("qa", force_deep=True) == "deep"


def test_chat_reports_degraded_servers_in_meta(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "degraded", lambda: ["maarif-mufredat"])
    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(
        rt.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(text="cevap", citations=[]))

    out = rt.chat([{"role": "user", "content": "merhaba"}])
    assert out["meta"]["degraded"] == ["maarif-mufredat"]


def test_empty_model_output_becomes_an_honest_message_not_a_blank_reply(tmp_path, monkeypatch):
    """A budget-exhausted loop can return text="" — measured in Task 4. The
    reader must never receive a blank answer."""
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])
    monkeypatch.setattr(rt.gemini, "chat_with_tools",
                        lambda *a, **k: ToolLoopResult(text="   ", budget_exhausted=True))

    out = rt.chat([{"role": "user", "content": "kesir nedir"}])
    assert out["answer"].strip()
    assert "kesir nedir" in out["answer"]


def test_chat_meta_carries_the_tool_ledger_and_dropped_count(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])
    monkeypatch.setattr(rt.gemini, "chat_with_tools", lambda *a, **k: ToolLoopResult(
        text="Kaynaklı [S1] ve uydurma [S5].",
        citations=[{"kind": "mufredat", "label": "MEB", "locator": {},
                    "snippet": "s", "confidence": 0.9}],
        tool_calls=[{"name": "kazanim_ara", "ms": 40, "ok": True}]))

    out = rt.chat([{"role": "user", "content": "kesir"}])

    assert out["meta"]["dropped_citations"] == 1
    assert out["meta"]["tool_calls"][0]["name"] == "kazanim_ara"
    assert "[S5]" not in out["answer"]
    assert len(out["citations"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_assistant_core.py -v -k "tier or degraded or ledger"`
Expected: FAIL — `AttributeError: type object 'AssistantRuntime' has no attribute '_tier_for'`

- [ ] **Step 3: Wire the runtime**

`AssistantRuntime.__init__` sonuna ekle:

```python
        from src.assistant_tools import build_registry
        self.registry = build_registry(self._local_search)
```

Ve yardımcıyı ekle:

```python
    def _local_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """The retriever, shaped as a tool the model can choose to call."""
        return self._load_retriever().search(query, top_k=top_k)

    DEEP_INTENTS = frozenset({"study_plan", "grade_analysis", "exam_solving"})

    @classmethod
    def _tier_for(cls, intent: str, force_deep: bool) -> str:
        # Deterministic on purpose: the same question must pick the same tier,
        # so latency and quota use stay predictable.
        return "deep" if (force_deep or intent in cls.DEEP_INTENTS) else "fast"
```

**`SYSTEM_PROMPT`'u sınıf sabitine çıkar (Task 6'nın kendi ön koşulu).**
`_build_conversation` `self.SYSTEM_PROMPT` okuyor ama o sabit henüz yok — Task 7 üretiyor.
`_build_conversation` `chat()` içinde `try` bloğunun DIŞINDA çağrıldığı için, sabit olmadan
`chat()`'e giren her test `AttributeError` ile düşer. Çözüm bir yer tutucu değil, **birebir
çıkarma**: `_generate_answer` içindeki mevcut `system_prompt` yerel değişkeninin metnini
(`src/assistant_core.py:1524-1548`) karakteri karakterine `AssistantRuntime.SYSTEM_PROMPT`
sınıf sabitine taşı. `_generate_answer` zaten bu task'ta siliniyor; metin kaybolmasın diye
taşınıyor. Davranış değişmiyor — yeniden yazımı Task 7 yapacak.

```python
    SYSTEM_PROMPT = (
        # _generate_answer'dan birebir taşındı. İçeriği Task 7 yeniden yazar.
        "Sen TEDY Eğitim Asistanısın — ortaokul öğrencisi Işık ve ailesi için kişisel eğitim danışmanısın.\n\n"
        ...  # mevcut metnin TAMAMI, tek karakter değiştirmeden
    )
```

**Atıf numarası sözleşmesini modele GÖSTER (bu task'ın en kritik parçası).**

Ölçülen kusur: `chat_with_tools` araç sonucunu modele
`[araç:{ad} girdi={...}]\n{gövde}` olarak besliyor — **içinde hiç `[S]` numarası yok.**
Ama sistem promptu modelden `[S1]`, `[S2]` yazmasını istiyor ve `_finalize_citations`
numaraları `out.citations`'a eklenme sırasına göre atıyor. Model hangi kaynağın kaç
numara olduğunu bilmiyor; bir araç çağrısı birden çok kaynak döndürebildiği için
çağrıları sayarak da bilemez.

Sonucu düşen bir işaretleyici DEĞİL: model `[S2]` yazarsa `_finalize_citations` onu
mevcut ikinci kaynağa memnuniyetle bağlar ve panele **gerçek ama iddiayı desteklemeyen**
bir kaynak girer. Bu, uydurma yasağının en tehlikeli biçimidir — sessiz, kendinden emin,
yanlış. Hiçbir mevcut test yakalamaz, çünkü hepsi atıf listesini elle kuruyor.

Düzeltme `chat_with_tools`'un transkript kurgusunda (`src/assistant_core.py`, `outcome.ok`
dalı). Kaynaklar eklenirken atanacak numaralar modele bildirilir:

```python
                if outcome.ok:
                    first = len(out.citations) + 1
                    out.citations.extend(outcome.citations)
                    # Modelin gördüğü numaralar ile _finalize_citations'ın atadığı
                    # numaralar AYNI sayaçtan gelmeli; yoksa model doğru cümleye
                    # yanlış kaynağı bağlar ve bu panelde doğrulanmış görünür.
                    marks = "\n".join(
                        f"[S{first + j}] {c.get('label', '')}"
                        for j, c in enumerate(outcome.citations)
                    )
                    body = f"{marks}\n{outcome.text}" if marks else outcome.text
                else:
                    body = f"HATA: {outcome.error}"
```

**Gereken test** (`tests/test_assistant_models.py`'a ekle):

```python
def test_the_model_is_shown_which_number_each_source_will_get():
    """Numbering is assigned by _finalize_citations in accumulation order. If the
    model never sees those numbers it cites by guesswork, and a wrong-but-real
    source is worse than a dropped marker: it looks verified."""
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])

    def dispatch(name, args):
        return ToolOutcome(ok=True, text="gövde", citations=[
            {"kind": "mufredat", "label": "kazanım A", "locator": {},
             "snippet": "s", "confidence": 0.9},
            {"kind": "mufredat", "label": "kazanım B", "locator": {},
             "snippet": "s", "confidence": 0.9},
        ])

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)
    shown = c._client.models.contents[-1]
    assert "[S1] kazanım A" in shown
    assert "[S2] kazanım B" in shown
    # Ve gösterilen numaralar finalize'ın atayacağıyla aynı olmalı.
    assert [x["label"] for x in out.citations] == ["kazanım A", "kazanım B"]
```

`chat()` gövdesini değiştir — retrieval-öncesi arama kaldırılır, yerine döngü gelir:

```python
    def chat(
        self,
        messages: list[dict[str, Any]],
        session_id: str = "",
        context_filters: dict[str, Any] | None = None,
        temperature: float = 0.2,
        force_deep: bool = False,
    ) -> dict[str, Any]:
        start = time.perf_counter()

        user_query = self._latest_user_message(messages)
        safety_flags = self.policy.evaluate(user_query)
        intent = self._classify_intent(user_query)
        tier = self._tier_for(intent, force_deep)

        if self._is_context_stale():
            safety_flags.append("warning:stale_context")

        convo = self._build_conversation(messages, user_query, intent, safety_flags)

        try:
            loop = self.gemini.chat_with_tools(
                messages=convo,
                declarations=self.registry.declarations(),
                dispatch=self.registry.dispatch,
                tier=tier,
                max_output_tokens=8192 if tier == "deep" else 2048,
                temperature=temperature,
            )
        except Exception as exc:
            logger.error("Assistant tool loop failed: %s", exc)
            loop = ToolLoopResult(text=self._fallback_answer(user_query))

        if not loop.text.strip():
            # The loop can legitimately return empty text — a model asked with
            # its tools withdrawn is not obliged to say anything. Without this
            # the reader gets a blank reply, which is worse than an honest one:
            # measured during Task 4, a budget-exhausted loop yields text="".
            logger.warning("Assistant produced no text (budget_exhausted=%s)",
                           loop.budget_exhausted)
            loop.text = self._fallback_answer(user_query)

        answer, citations, dropped = self._finalize_citations(
            loop.text, loop.citations)

        # Eski chat() bu bayrağı zayıf retrieval'dan set ediyordu. Retrieval ön
        # adımı kalkıyor ama bayrağın anlamı kalkmıyor: cevabın arkasında kaynak
        # yoksa okur bunu bilmeli. Yeni mimarideki karşılığı, çözülmüş atıf
        # listesinin boş olmasıdır.
        if not citations:
            safety_flags.append("warning:limited_confidence")

        answer += self.policy.guidance_suffix(safety_flags)

        latency_ms = int((time.perf_counter() - start) * 1000)
        payload = {
            "answer": answer,
            "citations": citations,
            "safety_flags": sorted(set(safety_flags)),
            "plan_blocks": [],
            "intent": intent,
            "session_id": session_id,
            "meta": {
                "model": self.gemini.last_model_used or "gemini",
                "provider": "gemini",
                "tier": tier,
                "tool_calls": loop.tool_calls,
                "dropped_citations": dropped,
                "degraded": self.registry.degraded(),
                "budget_exhausted": loop.budget_exhausted,
                "retrieval_count": len(citations),
                "latency_ms": latency_ms,
                "index_generated_at": self._meta_generated_at(),
            },
        }

        self._write_metric({
            "type": "chat", "session_id": session_id, "intent": intent,
            "tier": tier, "latency_ms": latency_ms, "citations": len(citations),
            "tool_calls": len(loop.tool_calls),
            "safety_flags": payload["safety_flags"],
            "timestamp": _utcnow_naive().isoformat() + "Z",
        })
        return payload
```

`_generate_answer()`'ı sil ve yerine iki yardımcı koy:

```python
    def _build_conversation(
        self,
        messages: list[dict[str, Any]],
        user_query: str,
        intent: str,
        safety_flags: list[str],
    ) -> list[dict[str, str]]:
        """System prompt plus recent turns.

        Retrieved context is deliberately absent: it used to be pasted in here
        whether or not the question called for it, which is how raw EBA OCR
        ended up under every answer. Evidence now enters through the tools.
        """
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *[
                {"role": str(m.get("role", "user")),
                 "content": str(m.get("content", ""))[:2000]}
                for m in messages[-3:] if isinstance(m, dict)
            ],
            {"role": "user", "content": (
                f"Soru türü: {intent}\n"
                f"Güvenlik: {', '.join(safety_flags) if safety_flags else 'yok'}\n\n"
                f"Soru: {user_query}"
            )},
        ]

    @staticmethod
    def _fallback_answer(user_query: str) -> str:
        return (
            "Şu anda bu soruya cevap üretemedim. Soruyu biraz daha belirgin "
            f"(ders/konu/tarih) biçimde tekrar gönderir misin?\n\n"
            f"Sorduğun: {user_query}"
        )
```

`study_plan()`'i de aynı döngüye bağla — gövdesindeki retrieval çağrısını kaldır ve şununla değiştir:

```python
    def study_plan(
        self,
        messages: list[dict[str, Any]],
        session_id: str = "",
        context_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        out = self.chat(
            messages=messages,
            session_id=session_id,
            context_filters=context_filters,
            force_deep=True,
        )
        out["intent"] = "study_plan"
        out["plan_blocks"] = self._build_rule_based_plan(
            self._latest_user_message(messages))
        return out
```

Kural tabanlı `_build_rule_based_plan()` bugünkü gibi kalır; artık yanına araçlarla temellendirilmiş bir anlatı gelir.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_assistant_core.py tests/test_assistant_api.py -v`

**Expected: dört yeni test PASS, ama MEVCUT İKİ TEST KIRILIR — ikisi de bu değişimin
gerçek sonucudur, önceden var olan arıza değildir. İkisini de güncelle:**

1. `test_chat_returns_citations_and_answer` — `runtime.router`'ı sahte bir nesneyle
   değiştiriyor. Ama `__init__` içinde `self.router = self.gemini` (AYNI nesne), ve yeni
   `chat()` `self.gemini.chat_with_tools()` çağırıyor. `runtime.router`'a yeni bir nesne
   atamak `runtime.gemini`'yi değiştirmez → test **gerçek Gemini'ye ağdan çıkar**. Bu,
   "hiçbir otomatik test ağa çıkmaz" kısıtının ihlalidir. Düzelt: sahteyi
   `monkeypatch.setattr(runtime.gemini, "chat_with_tools", lambda *a, **k: ToolLoopResult(...))`
   biçiminde kur ve assertion'ı yeni cevap şekline göre güncelle.
2. `test_chat_marks_limited_confidence_when_retrieval_weak` — bayrağın kaynağı değişti
   (zayıf retrieval → boş atıf listesi). Testin adı ve kurgusu yeni sebebi anlatacak biçimde
   güncellenmeli; **iddiası zayıflatılmamalı** — bayrak hâlâ set edilmeli.

Bu iki testi güncellemek bu task'ın kapsamındadır, ayrı bir task değildir. Tam süit
(`python -m pytest -q`) task sonunda yeşil olmalı.

- [ ] **Step 5: Uçtan uca elle doğrulama**

```bash
python -c "
from src.assistant_core import AssistantRuntime
rt = AssistantRuntime('.')
out = rt.chat([{'role':'user','content':'6. sınıf fen dersinde kuvvet konusunda hangi kazanımlar var?'}])
print(out['answer'][:400]); print()
print('araçlar:', [t[\"name\"] for t in out['meta']['tool_calls']])
print('kaynak türleri:', [c['kind'] for c in out['citations']])
print('degraded:', out['meta']['degraded'])
"
```
Expected: `kazanim_ara` çağrılmış, kaynaklarda `mufredat` var, `degraded` boş.

- [ ] **Step 6: OpenAI-uyumlu ucun ve planın hâlâ çalıştığını doğrula**

`meta` zarfı genişledi; `/v1/chat/completions` alanları jenerik geçiriyor ama bu
sözleşme üçüncü taraflarca kullanılıyor, kırılmadığı kanıtlanmalı.

```bash
python -c "
from src.assistant_core import AssistantRuntime
rt = AssistantRuntime('.')
r = rt.openai_chat_completion({'messages':[{'role':'user','content':'bugün ne var'}]})
assert r['object'] == 'chat.completion', r
assert 'meta' in r and 'tier' in r['meta'], r['meta']
print('openai ucu tamam · tier:', r['meta']['tier'])

p = rt.study_plan([{'role':'user','content':'haftalık çalışma planı'}])
assert p['intent'] == 'study_plan'
assert p['meta']['tier'] == 'deep', p['meta']
print('plan tamam · blok sayısı:', len(p['plan_blocks']))
"
```
Expected: iki satır da yazdırılıyor, assert yok.

- [ ] **Step 7: Commit**

```bash
git add src/assistant_core.py tests/test_assistant_core.py
git commit -m "feat: route assistant answers through the tool loop

Retrieval no longer runs unconditionally ahead of the prompt, which is what
pasted raw EBA OCR into every answer regardless of the question. The retriever
is now a tool the model calls when the question is about Işık's own records.

Tier selection is deterministic — by intent, or when the reader explicitly
asks to go deeper — so the same question always costs the same."
```

---

## Task 7: Sistem promptu — DEHB pedagojisi ve kaynak sadakati

**Files:**
- Modify: `src/assistant_core.py` (`_build_conversation` içindeki sistem promptu)
- Test: `tests/test_assistant_core.py` (genişletilir)

**Interfaces:**
- Consumes: Task 6 `_build_conversation`
- Produces: `AssistantRuntime.SYSTEM_PROMPT: str`

- [ ] **Step 1: Write the failing test**

```python
def test_system_prompt_forbids_inventing_locators():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "uydurma" in p.lower()
    for token in ("kazanım kodu", "sayfa numarası"):
        assert token in p.lower()


def test_system_prompt_names_the_authority_split():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "ogrenci_verisi_ara" in p
    assert "kazanim_ara" in p


def test_system_prompt_keeps_the_citation_contract():
    assert "[S1]" in AssistantRuntime.SYSTEM_PROMPT


def test_system_prompt_no_longer_bans_citation_markers():
    """The old prompt ended with 'never finish with a Kaynaklar list' AND the
    frontend stripped markers — together they made citation impossible."""
    assert "Kaynaklar:' listesiyle bitirme" not in AssistantRuntime.SYSTEM_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_assistant_core.py -v -k system_prompt`

Expected: **3 FAIL, 1 PASS** — `AttributeError` DEĞİL. Task 6 `SYSTEM_PROMPT`'u mevcut
prompttan birebir çıkarıp sınıf sabiti yaptı, yani sabit artık var.
`test_system_prompt_keeps_the_citation_contract` baştan yeşildir — eski prompt da
`[S1]` atıf sözleşmesini zaten taşıyor, ve bunun korunması istenen davranıştır.
Diğer üçü kırmızıdır: eski promptta "uydurma" yok, araç adları (`kazanim_ara`,
`ogrenci_verisi_ara`) yok, ve yasaklanması istenen `"Kaynaklar:' listesiyle bitirme"`
cümlesi hâlâ içinde. Adım 3 bu üçünü yeşile çevirir.

**Prompt'ta ZORUNLU madde (Task 6'nın atıf sözleşmesiyle eşleşir):** araç sonuçlarında
modele `[S1] <etiket>` biçiminde numaralar gösteriliyor. Prompt açıkça şunu demeli:
*yalnız araç sonuçlarında sana gösterilen `[S]` numaralarını kullan; numara uydurma,
kendin saymaya çalışma.* Bu cümle olmadan Task 6'nın numaralandırma düzeltmesi yarım kalır.

- [ ] **Step 3: Write the prompt**

`AssistantRuntime` içine sınıf sabiti olarak ekle ve `_build_conversation`'da kullan:

```python
    SYSTEM_PROMPT = (
        "Sen TEDY Eğitim Asistanısın — 6. sınıf öğrencisi Işık ve ailesi için "
        "kişisel eğitim danışmanısın. Varsayılan dil Türkçe.\n\n"

        "## Hangi araca ne zaman uzanırsın\n"
        "- Işık'a özel her soru (ödev, sınav, not, ders programı, duyuru) → "
        "`ogrenci_verisi_ara`. Bu veriler yalnız orada bulunur.\n"
        "- Konu, kavram, müfredat, kazanım sorusu → `kazanim_ara`, "
        "`mufredat_ara`, `kitap_listele` + `kitap_sayfa`. MEB korpusu bu "
        "konularda tek otoritedir.\n"
        "- Görsel/şema açıklaman gerekiyorsa → `figur_ara`, sonra `figur_getir`.\n"
        "- İkisini karıştırma: Işık'ın notunu müfredattan, kazanımı yerel "
        "dosyadan çıkarma.\n\n"

        "## Uydurma yasağı\n"
        "- Kazanım kodu, ders kitabı adı ve sayfa numarası YALNIZ araç "
        "çıktısından gelir. Hiçbirini hatırlayarak veya tahmin ederek yazma.\n"
        "- Araç sonuç döndürmediyse eksikliği açıkça söyle. Boşluğu doldurma.\n"
        "- Kaynağı çürüten veya kaynakta olmayan bir olgu ekleme.\n\n"

        "## Atıf\n"
        "- Araçtan gelen her bilgiyi kullandığın cümlede [S1], [S2] biçiminde "
        "işaretle. İşaretler kullanıcıya tıklanabilir kaynak olarak gösterilir.\n"
        "- Yanıtın sonuna ayrı kaynak listesi ekleme; atıf satır içindedir.\n\n"

        "## Nasıl anlatırsın (DEHB-dostu)\n"
        "- İlk cümlede doğrudan cevabı ver.\n"
        "- Anlatımı 3–6 dakikada tüketilebilir parçalara böl; her parçanın "
        "kendi başlığı olsun.\n"
        "- Adımları numaralandır ve her adıma tahmini süre yaz — 'neredeyim' "
        "sorusunun cevabı görünür olsun.\n"
        "- Somut ol: ne yapılacak, ne zaman, ne kadar sürede.\n"
        "- Başarıyı önce söyle, eksiği sonra ve yapıcı biçimde.\n"
        "- Uzun paragraf yazma; madde işareti ve kısa cümle kullan.\n\n"

        "## Sınırlar\n"
        "- Klinik tanı koyma, tedavi önerme.\n"
        "- Riskli psikolojik durumda profesyonel destek yönlendirmesi yap."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_assistant_core.py -v -k system_prompt`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/assistant_core.py tests/test_assistant_core.py
git commit -m "feat: rewrite the assistant prompt around tools and ADHD pedagogy

The old prompt described sources the model could not reach and ended by
banning the very citation list its markers implied. It now says which tool
answers which kind of question, forbids recalling a learning-outcome code or
page number from memory, and asks for the chunked, numbered, time-boxed shape
that suits the reader this assistant was built for."
```

---

## Task 8: Stilleri ayır ve Carbon AI token'larına geçir

**Files:**
- Create: `dashboard/src/components/AssistantChat.scss`
- Modify: `dashboard/src/theme/ted-theme.scss` (`.ac*` blokları silinir, ~2606-2930)
- Modify: `dashboard/src/components/AssistantChat.tsx` (import satırı)

**Interfaces:**
- Consumes: `@carbon/themes` AI token'ları, `@carbon/styles` `ai-gradient` mixin'leri
- Produces: `.ac`, `.ac-msg`, `.ac__*` sınıfları (aynı adlar korunur), yeni `.ac-msg--assistant` AI yüzeyi

**Ön koşul:** `feat/carbon-token-fidelity` dalı bu dala merge edilmiş olmalı. Aradığımız düzeltme orada: `:root { @include theme.theme(themes.$g10); }`. O olmadan `--cds-ai-*` `:root` altında çözülmez ve bu task'ın tüm görsel etkisi sessizce kaybolur — build geçer, renkler yanlış olur.

- [ ] **Step 1: Ön koşulu doğrula**

```bash
grep -n "theme.theme(themes" dashboard/src/theme/ted-theme.scss
```
Expected: `:root` bloğu içinde bir eşleşme.

Eşleşme yoksa önce merge et, sonra tekrar doğrula:

```bash
git merge feat/carbon-token-fidelity
grep -n "theme.theme(themes" dashboard/src/theme/ted-theme.scss
```

Hâlâ yoksa DUR ve kullanıcıya bildir — bu task'ın tamamı ona bağımlıdır.

- [ ] **Step 2: Mevcut `.ac` bloğunu yeni dosyaya taşı**

```bash
cd dashboard/src
START=$(grep -n '^\.ac {' theme/ted-theme.scss | cut -d: -f1)
END=$(awk -v s="$START" 'NR>s && /^\.[a-z]/ && $0 !~ /^\.ac/ {print NR-1; exit}' theme/ted-theme.scss)
sed -n "${START},${END}p" theme/ted-theme.scss > components/AssistantChat.scss
sed -i "${START},${END}d" theme/ted-theme.scss
```

`AssistantChat.tsx`'in en üstüne ekle:

```tsx
import './AssistantChat.scss'
```

- [ ] **Step 3: Build'in hâlâ geçtiğini doğrula**

Run: `cd dashboard && npm run build`
Expected: başarılı. Görsel çıktı bu adımda değişmemeli — yalnız dosya taşındı.

- [ ] **Step 4: AI token'larını uygula**

`AssistantChat.scss` başına:

```scss
@use '@carbon/react/scss/theme' as theme;
@use '@carbon/react/scss/utilities/ai-gradient' as ai;
```

Sabit hex'leri değiştir ve AI yüzeyini kur:

```scss
// Carbon's AI surface language, not an imitation of it. Values come from the
// installed @carbon/themes; the Figma copies carry no subscribed library and
// are not the token-value authority in any case.
.ac-msg--assistant .ac-msg__body {
  @include ai.ai-gradient('left', 40%);
  border-radius: var(--ted-radius-card);
  padding: var(--ted-space-sm);
}

.ac__panel {
  background:
    linear-gradient(to top, theme.$layer, theme.$layer) padding-box,
    linear-gradient(to bottom, theme.$ai-border-start, theme.$ai-border-end) border-box;
  border: 1px solid transparent;
  box-shadow: 0 2px 6px theme.$ai-drop-shadow;
}

.ac__textarea .cds--text-area {
  box-shadow: inset 0 1px 3px theme.$ai-inner-shadow;

  &:focus {
    outline-color: theme.$ai-border-strong;
  }
}

// The prompt chips previously hard-coded #edf5ff / #0f62fe.
.ac__prompt-chip:hover:not(:disabled) {
  background: theme.$ai-aura-hover-background;
  border-color: theme.$ai-border-strong;
  color: theme.$text-primary;
}

.ac-msg--thinking .cds--skeleton__text {
  background: theme.$ai-skeleton-background;

  &::before {
    background: theme.$ai-skeleton-element-background;
  }
}

.ac__ref-item:hover {
  background:
    linear-gradient(to right, theme.$ai-aura-hover-start 0%, theme.$ai-aura-hover-end 50%),
    theme.$ai-aura-hover-background;
}
```

- [ ] **Step 5: Doğrula — sabit hex kalmadı, token sayısı hedefte**

```bash
cd dashboard/src/components
grep -nE "#edf5ff|#0f62fe" AssistantChat.scss && echo "BAŞARISIZ: sabit hex kaldı" || echo "TAMAM: sabit hex yok"
grep -oE "ai-[a-z0-9-]+" AssistantChat.scss | sort -u | wc -l
```
Expected: "TAMAM", ve sayım **≥ 11**. (Eşik ölçülerek 12'den 11'e indirildi: `ai-gradient` bir mixin'dir, kendi içinde token kullanır ama bu kullanım bizim dosyamıza grep atınca görünmez. 12 rakamı bunu sayabileceğini varsayıyordu; sayamıyor. Eşiği tutturmak için var olmayan bir UI durumuna token uydurma — sayım 11 ise geç. Popover token'ları Task 9'da eklenecek.)

- [ ] **Step 6: Build + görsel kontrol**

Run: `cd dashboard && npm run build && npm run lint`
Expected: ikisi de temiz.

- [ ] **Step 7: Commit**

```bash
git add dashboard/src/components/AssistantChat.scss dashboard/src/components/AssistantChat.tsx dashboard/src/theme/ted-theme.scss
git commit -m "feat: build the assistant surface on Carbon's AI tokens

The page used none of the twenty-one AI tokens Carbon ships, imitating them
with #edf5ff and #0f62fe instead. It now uses the real aura, border, shadow
and skeleton tokens through Carbon's own ai-gradient mixins, so the surface
tracks the theme rather than a snapshot of it.

The rules also move out of the 5142-line theme monolith into a file scoped to
this component."
```

**Not:** `ted-theme.scss`'te kullanıcının commit edilmemiş değişikliği var. Bu commit'te yalnız `.ac` bloğunun silinmesi yer almalı; `git add -p` ile o hunk'ı seç veya kullanıcının değişikliğini önce commit etmesini iste.

---

## Task 9: Markdown render ve atıf çipleri

**Files:**
- Create: `dashboard/src/components/CitationChip.tsx`
- Modify: `dashboard/src/utils/markdown.tsx` (`renderInline`, `RenderOptions`, `renderMarkdown`)
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `dashboard/src/types.ts`
- Modify: `dashboard/src/components/AssistantChat.scss`
- Test: `dashboard/tests/e2e/assistant-chat.spec.ts`, `dashboard/tests/e2e/books.spec.ts` (regresyon)

**Interfaces:**
- Consumes: `renderMarkdown(markdown, options)` — `dashboard/src/utils/markdown.tsx:190`; Task 5 atıf şeması
- Produces: `CitationChip({ citation, onActivate })`, `AssistantCitation` genişletilmiş tipi, `RenderOptions.renderToken?: (token: string, key: string) => ReactNode`

**Ön-uçuş kararı (BULGU B).** Metni `[S1]` sınırlarında bölüp her parçayı ayrı
`renderMarkdown`'dan geçirmek blok düzeyi markdown'ı kırar: `- madde [S1]` bölününce
çip `<li>`'nin dışına düşer. Bunun yerine metin **bir kez** render edilir ve
`renderMarkdown` satır-içi bir jeton kancası kabul eder. Kanca `[S\d+]` desenini
düz metin akışlarında yakalar, dolayısıyla çip hangi blok içindeyse orada durur.
Tedy Books `[S1]` üretmediği ve `renderToken` opsiyonel olduğu için okuyucu etkilenmez —
ama bu paylaşılan bir util olduğundan Adım 6'da bir okuyucu regresyon testi koşulur.

- [ ] **Step 1: Update the types**

`dashboard/src/types.ts`:

```ts
export type CitationKind = 'ogrenci' | 'mufredat' | 'kitap' | 'oer'

export interface AssistantCitation {
  id: string
  kind: CitationKind
  label: string
  locator: Record<string, unknown>
  snippet: string
  confidence: number
}

export interface AssistantToolCall {
  name: string
  ms: number
  ok: boolean
}
```

`AssistantResponse['meta']`'ya ekle:

```ts
    tier?: 'fast' | 'deep'
    tool_calls?: AssistantToolCall[]
    dropped_citations?: number
    degraded?: string[]
    budget_exhausted?: boolean
```

- [ ] **Step 2: Write the citation chip**

`dashboard/src/components/CitationChip.tsx`:

```tsx
import { useState } from 'react'
import { Popover, PopoverContent } from '@carbon/react'
import type { AssistantCitation } from '../types'

interface Props {
  citation: AssistantCitation
  onActivate: (id: string) => void
}

const KIND_LABEL: Record<AssistantCitation['kind'], string> = {
  ogrenci: 'Okul verisi',
  mufredat: 'MEB müfredatı',
  kitap: 'Ders kitabı',
  oer: 'Açık kaynak',
}

export default function CitationChip({ citation, onActivate }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <Popover open={open} align="bottom" autoAlign caret dropShadow={false}>
      <button
        type="button"
        className="ac-cite"
        aria-label={`${KIND_LABEL[citation.kind]}: ${citation.label}`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => onActivate(citation.id)}
      >
        {citation.id.replace('S', '')}
      </button>
      <PopoverContent className="ac-cite__pop">
        <span className="ac-cite__kind">{KIND_LABEL[citation.kind]}</span>
        <strong className="ac-cite__label">{citation.label}</strong>
        <p className="ac-cite__snippet">{citation.snippet}</p>
      </PopoverContent>
    </Popover>
  )
}
```

- [ ] **Step 3a: Give the markdown renderer an inline token hook**

`dashboard/src/utils/markdown.tsx`. `renderInline` bugün düz metin akışlarını doğrudan
`nodes.push(...)` ile ekliyor; kanca oraya girer.

```tsx
export type TokenRenderer = (token: string, key: string) => ReactNode

const CITATION_RE = /\[S\d+\]/g

/**
 * Push a plain-text run, handing any [S1] markers to the caller's renderer.
 *
 * Doing this inside renderInline rather than by splitting the source keeps a
 * citation in whatever block it was written in — a marker at the end of a list
 * item stays inside the <li> instead of landing after the list.
 */
function pushText(
  nodes: ReactNode[],
  text: string,
  key: string,
  renderToken?: TokenRenderer,
): void {
  if (!renderToken) {
    nodes.push(text)
    return
  }
  let last = 0
  let m: RegExpExecArray | null
  CITATION_RE.lastIndex = 0
  while ((m = CITATION_RE.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    nodes.push(renderToken(m[0], `${key}-c${m.index}`))
    last = m.index + m[0].length
  }
  if (last < text.length) nodes.push(text.slice(last))
}
```

`renderInline` imzasına üçüncü parametreyi ekle ve iki `nodes.push(text.slice(...))`
çağrısını `pushText`'e çevir:

```tsx
function renderInline(
  text: string,
  keyPrefix: string,
  renderToken?: TokenRenderer,
): ReactNode[] {
  const nodes: ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null
  INLINE_RE.lastIndex = 0

  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > last) {
      pushText(nodes, text.slice(last, match.index), `${keyPrefix}-${last}`, renderToken)
    }
    const token = match[0]
    const key = `${keyPrefix}-${match.index}`
    if (token.startsWith('**') || token.startsWith('__')) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    } else if (token.startsWith('`')) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>)
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>)
    }
    last = match.index + token.length
  }

  if (last < text.length) {
    pushText(nodes, text.slice(last), `${keyPrefix}-${last}`, renderToken)
  }
  return nodes
}
```

`RenderOptions`'a ekle:

```tsx
interface RenderOptions {
  /** Enlarge the opening letter of the first paragraph, as a printed book does. */
  dropCap?: boolean
  /** Replace inline [S1]-style markers — used by the assistant for citations. */
  renderToken?: TokenRenderer
}
```

`renderMarkdown` gövdesindeki **her** `renderInline(...)` çağrısına üçüncü argüman
olarak `options.renderToken` geçir. Çağrı yerlerini bul ve hiçbirini atlama:

```bash
grep -n "renderInline(" dashboard/src/utils/markdown.tsx
```

- [ ] **Step 3b: Render the answer once, with chips inline**

`AssistantChat.tsx`: `stripInlineCitations()` fonksiyonunu **tamamen sil** ve çağrısını kaldır.

```tsx
import { renderMarkdown } from '../utils/markdown'
import CitationChip from './CitationChip'

function AnswerBody({
  text,
  citations,
  onActivate,
}: {
  text: string
  citations: AssistantCitation[]
  onActivate: (id: string) => void
}) {
  const byId = useMemo(
    () => new Map(citations.map(c => [c.id, c])),
    [citations],
  )

  return (
    <>
      {renderMarkdown(text, {
        renderToken: (token, key) => {
          const citation = byId.get(token.slice(1, -1))
          // A marker the backend could not resolve should not have survived,
          // but if one does, show its text rather than swallowing it.
          if (!citation) return <span key={key}>{token}</span>
          return <CitationChip key={key} citation={citation} onActivate={onActivate} />
        },
      })}
    </>
  )
}
```

Mesaj gövdesindeki `<p className="ac-msg__content">{msg.content}</p>` satırını değiştir:

```tsx
<div className="ac-msg__content">
  {msg.role === 'assistant'
    ? <AnswerBody text={msg.content} citations={msg.citations ?? []} onActivate={setActiveCitation} />
    : msg.content}
</div>
```

`const [activeCitation, setActiveCitation] = useState<string | null>(null)` ekle.

- [ ] **Step 4: Style the chip with the AI popover tokens**

`AssistantChat.scss`'e ekle:

```scss
.ac-cite {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-inline-size: 1.15rem;
  block-size: 1.15rem;
  margin-inline: 0.15rem;
  padding: 0 0.3rem;
  border: 1px solid theme.$ai-border-strong;
  border-radius: 999px;
  background: theme.$ai-aura-hover-background;
  color: theme.$text-primary;
  font-size: 0.6875rem;
  line-height: 1;
  cursor: pointer;
  vertical-align: super;

  &:hover { background: theme.$ai-aura-hover-start; }
  &:focus-visible { outline: 2px solid theme.$ai-border-strong; }
}

.ac-cite__pop {
  @include ai.ai-popover-gradient();
  max-inline-size: 22rem;
  padding: var(--ted-space-sm);
  box-shadow:
    0 4px 12px theme.$ai-popover-shadow-outer-01,
    0 2px 4px theme.$ai-popover-shadow-outer-02;
}

.ac-cite__kind {
  display: block;
  font-size: 0.6875rem;
  color: theme.$text-secondary;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
```

- [ ] **Step 5: Playwright test**

`dashboard/tests/e2e/assistant-chat.spec.ts` oluştur:

```ts
import { test, expect } from '@playwright/test'

test('assistant answers render markdown rather than raw syntax', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      answer: '## Başlık\n\n- birinci madde\n- ikinci madde [S1]',
      citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir',
                    locator: {}, snippet: 'kazanım metni', confidence: 0.9 }],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesirler')
  await page.getByLabel('Gönder').click()

  await expect(page.locator('.ac-msg__content h2')).toHaveText('Başlık')
  await expect(page.locator('.ac-msg__content li')).toHaveCount(2)
  await expect(page.locator('.ac-msg__content')).not.toContainText('##')
  await expect(page.locator('.ac-cite')).toHaveText('1')
})
```

- [ ] **Step 6: Run the tests, including the reader regression**

`markdown.tsx` Tedy Books okuyucusuyla paylaşılıyor. `renderToken` opsiyonel olduğu için
davranış değişmemeli — bunu iddia etme, koş:

```bash
cd dashboard && npm run build && npm run lint
npx playwright test assistant-chat
npx playwright test books        # okuyucu regresyonu; mevcut spec'ler geçmeli
```
Expected: hepsi PASS. `books` spec'i yoksa bunun yerine okuyucuyu elle aç ve bir bölümün
başlık/paragraf/verse render'ının bozulmadığını doğrula.

- [ ] **Step 7: Commit**

```bash
git add dashboard/src/utils/markdown.tsx dashboard/src/components/CitationChip.tsx dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss dashboard/src/types.ts dashboard/tests/e2e/assistant-chat.spec.ts
git commit -m "feat: render assistant answers as markdown with live citations

Answers were printed into a <p>, so the bullets and headings the prompt asked
for arrived as literal '- ' and '##'. They now go through the renderer this
repo already had.

The [S1] markers are no longer stripped. Each becomes a chip that opens the
passage behind it in a Carbon AI popover, which is the first time the text and
the source panel are actually connected."
```

---

## Task 10: Kaynak paneli, mesaj eylemleri, degradasyon rozeti

**Files:**
- Create: `dashboard/src/components/SourcePanel.tsx`
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `dashboard/src/components/AssistantChat.scss`

**Interfaces:**
- Consumes: Task 9 `AssistantCitation`, `activeCitation` state
- Produces: `SourcePanel({ citations, activeId })`

- [ ] **Step 1: Write the source panel**

`dashboard/src/components/SourcePanel.tsx`:

```tsx
import { useEffect, useRef } from 'react'
import { Tag, Tile } from '@carbon/react'
import { DocumentView } from '@carbon/icons-react'
import type { AssistantCitation, CitationKind } from '../types'

const GROUP_ORDER: CitationKind[] = ['ogrenci', 'mufredat', 'kitap', 'oer']

const GROUP_TITLE: Record<CitationKind, string> = {
  ogrenci: 'Işık’ın okul verisi',
  mufredat: 'MEB müfredatı',
  kitap: 'Ders kitabı',
  oer: 'Açık eğitsel kaynak',
}

interface Props {
  citations: AssistantCitation[]
  activeId: string | null
}

export default function SourcePanel({ citations, activeId }: Props) {
  const activeRef = useRef<HTMLLIElement>(null)

  useEffect(() => {
    if (activeId) activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [activeId])

  if (citations.length === 0) {
    return (
      <Tile className="ac__panel">
        <h4 className="ac__panel-title"><DocumentView size={16} /> Kaynaklar</h4>
        <p className="ac__muted">Soru sorduğunda kaynaklar burada görünecek.</p>
      </Tile>
    )
  }

  return (
    <Tile className="ac__panel">
      <h4 className="ac__panel-title"><DocumentView size={16} /> Kaynaklar</h4>
      {GROUP_ORDER.map(kind => {
        const group = citations.filter(c => c.kind === kind)
        if (group.length === 0) return null
        return (
          <section key={kind} className="ac__ref-group">
            <h5 className="ac__ref-group-title">{GROUP_TITLE[kind]}</h5>
            <ul className="ac__ref-list">
              {group.map(c => (
                <li
                  key={c.id}
                  ref={c.id === activeId ? activeRef : undefined}
                  className={`ac__ref-item${c.id === activeId ? ' ac__ref-item--active' : ''}`}
                >
                  <span className="ac__ref-index">{c.id.replace('S', '')}</span>
                  <div>
                    <span className="ac__ref-path">{c.label}</span>
                    <p className="ac__ref-snippet">{c.snippet}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </Tile>
  )
}
```

- [ ] **Step 2: Add message actions and the degradation badge**

**Ön-uçuş kararı (BULGU C).** `regenerate()` ve `lastUserContent()` ne planda ne de
`AssistantChat.tsx`'te tanımlıydı. Önce ikisini yaz — mesaj listesinde verilen asistan
mesajından geriye doğru en yakın kullanıcı mesajını bulan tek bir yardımcı yeter:

```tsx
/** The user turn that produced a given assistant message, if any. */
function promptBehind(msgs: ChatMessage[], assistantId: string): string | null {
  const idx = msgs.findIndex(m => m.id === assistantId)
  if (idx < 0) return null
  for (let i = idx - 1; i >= 0; i -= 1) {
    if (msgs[i].role === 'user') return msgs[i].content
  }
  return null
}
```

Bileşen içinde:

```tsx
  function regenerate(assistantId: string) {
    const prompt = promptBehind(messages, assistantId)
    if (!prompt) return
    // Drop the answer being replaced so the new one does not read as a second
    // reply to the same question.
    setMessages(prev => prev.filter(m => m.id !== assistantId))
    void submit('chat', prompt)
  }

  function deepen(assistantId: string) {
    const prompt = promptBehind(messages, assistantId)
    if (prompt) void submit('chat', prompt, { deep: true })
  }
```

Sonra mesaj gövdesinin altına:

```tsx
{msg.role === 'assistant' && msg.id !== 'welcome' && (
  <div className="ac-msg__actions">
    <IconButton kind="ghost" size="sm" label="Kopyala"
      onClick={() => void navigator.clipboard.writeText(msg.content)}>
      <Copy />
    </IconButton>
    <IconButton kind="ghost" size="sm" label="Yeniden üret"
      onClick={() => void regenerate(msg.id)}>
      <Renew />
    </IconButton>
    <Button kind="ghost" size="sm" renderIcon={Search}
      onClick={() => deepen(msg.id)}>
      Daha derine in
    </Button>
  </div>
)}
```

Mesaj gövdesinin **üstüne**, degradasyon uyarısı:

```tsx
{msg.degraded && msg.degraded.length > 0 && (
  <div className="ac-msg__degraded">
    <Tag type="gray" size="sm">
      {msg.degraded.includes('maarif-mufredat')
        ? 'Müfredat kaynağına ulaşılamadı — yalnız okul verisiyle yanıtlandı'
        : 'Bazı kaynaklara ulaşılamadı'}
    </Tag>
  </div>
)}
```

**Güvenlik bayraklarının şiddetini ayır (Task 6'nın ölçülen sonucu).**

Bugün `AssistantChat.tsx:248` her bayrağı ayrımsız `<Tag type="red">{f}</Tag>` olarak basıyor.
İki sorun var ve ikincisi Task 6 ile büyüdü:

1. **Ham token okura gösteriliyor.** Rozetin metni tam olarak `warning:limited_confidence`.
   Bu bir 6. sınıf öğrencisinin ekranında iç değişken adı demek.
2. **Şiddet ayrımı yok.** `warning:limited_confidence` ile `risk:mental_health_crisis`
   aynı kırmızı. Task 6 `limited_confidence`'ı "çözülmüş atıf listesi boş" koşuluna bağladı,
   yani araç çağırmayı gerektirmeyen her sade cevap ("merhaba") artık bu bayrağı taşıyor.
   Kırmızı kriz rozetiyle aynı görünen bir "bilgi" rozeti, sık göründükçe gerçek kriz
   rozetini de değersizleştirir — bu, sessiz arıza yasağının okur tarafındaki karşılığıdır.

Bayrağın kendisi doğru ve kalmalı (cevabın arkasında gerçekten kaynak yok). Değişecek olan
sunumu:

```tsx
const FLAG_LABELS: Record<string, string> = {
  'warning:limited_confidence': 'Kaynaksız cevap',
  'warning:stale_context': 'Veriler güncel olmayabilir',
}

function flagTone(f: string): 'red' | 'gray' {
  return f.startsWith('risk:') ? 'red' : 'gray'
}

// render:
<Tag key={f} type={flagTone(f)} size="sm">{FLAG_LABELS[f] ?? f}</Tag>
```

`risk:*` kırmızı kalır — o ayrım yük taşıyor. `warning:*` gri olur. Sözlükte karşılığı
olmayan bayrak ham hâliyle basılır (sessizce yutulmaz).

**Gereken Playwright testi:** bir cevap hem `risk:` hem `warning:` bayrağı taşıdığında
ikisinin FARKLI `Tag` tipiyle render edildiğini doğrula; ve `warning:limited_confidence`
rozetinin metninin ham token OLMADIĞINI.

`ChatMessage` arayüzüne `degraded?: string[]` ekle ve API yanıtından doldur. `submit()` imzasına `opts?: { deep?: boolean }` ekle; `deep` ise gövdeye `force_deep: true` koy.

Yan paneli `SourcePanel`'e devret:

```tsx
<SourcePanel citations={latestAssistant?.citations ?? []} activeId={activeCitation} />
```

- [ ] **Step 3: Style the additions**

```scss
.ac__ref-group-title {
  margin: var(--ted-space-sm) 0 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: theme.$text-secondary;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.ac__ref-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background 0.15s ease;
}

.ac__ref-item--active {
  background:
    linear-gradient(to right, theme.$ai-aura-start 0%, theme.$ai-aura-end 60%),
    theme.$ai-aura-hover-background;
  outline: 1px solid theme.$ai-border-strong;
}

.ac__ref-index {
  flex: 0 0 auto;
  inline-size: 1.15rem;
  block-size: 1.15rem;
  border: 1px solid theme.$ai-border-strong;
  border-radius: 999px;
  font-size: 0.6875rem;
  text-align: center;
  line-height: 1.05rem;
}

.ac-msg__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-block-start: 0.35rem;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.ac-msg:hover .ac-msg__actions,
.ac-msg:focus-within .ac-msg__actions { opacity: 1; }

.ac-msg__degraded { margin-block-end: 0.35rem; }
```

- [ ] **Step 4: Extend the Playwright spec**

```ts
test('sources are grouped by kind and the cited one highlights', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Ödevin [S1] ve kazanım [S2].',
      citations: [
        { id: 'S1', kind: 'ogrenci', label: 'scraped_data.json', locator: {}, snippet: 'ödev', confidence: 0.8 },
        { id: 'S2', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'kazanım', confidence: 0.9 },
      ],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'ödevim ne')
  await page.getByLabel('Gönder').click()

  await expect(page.locator('.ac__ref-group')).toHaveCount(2)
  await expect(page.locator('.ac__ref-group-title').first()).toContainText('okul verisi')

  await page.locator('.ac-cite').first().click()
  await expect(page.locator('.ac__ref-item--active')).toHaveCount(1)
})

test('a degraded answer says so', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      answer: 'Yalnız okul verisiyle yanıt.', citations: [],
      safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
      meta: { model: 'gemini-3.7-flash', degraded: ['maarif-mufredat'], dropped_citations: 0 },
    }),
  }))

  await page.goto('/asistan')
  await page.fill('#ac-input', 'kesir')
  await page.getByLabel('Gönder').click()

  await expect(page.locator('.ac-msg__degraded')).toContainText('Müfredat kaynağına ulaşılamadı')
})
```

- [ ] **Step 5: Run the tests**

Run: `cd dashboard && npm run build && npm run lint && npx playwright test assistant-chat`
Expected: hepsi PASS

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/components/SourcePanel.tsx dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss dashboard/tests/e2e/assistant-chat.spec.ts
git commit -m "feat: group assistant sources by kind and say when one is missing

Every source card looked identical at a uniform 80%, whether it came from
Işık's homework file or a curriculum outcome. Cards are now grouped under the
authority they came from and carry a real locator, and clicking a citation
highlights the card it refers to.

An answer produced without a source that should have been there now says so on
the message, instead of looking like a complete answer."
```

---

## Task 11: SSE akışı ve gunicorn worker sınıfı

**Files:**
- Modify: `src/dashboard_api.py` (yeni uç)
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `~/.config/systemd/user/ted-dashboard.service`
- Test: `tests/test_dashboard_api.py` (genişletilir)

**Interfaces:**
- Consumes: Task 6 `AssistantRuntime.chat`
- Produces: `POST /api/assistant/stream` — `text/event-stream`, olaylar: `tool_start`, `tool_end`, `answer`, `done`

- [ ] **Step 1: Write the failing test**

`tests/test_dashboard_api.py` sonuna ekle:

```python
def test_assistant_stream_emits_tool_events_then_the_answer(client, monkeypatch):
    import src.dashboard_api as api

    class _Rt:
        def chat_events(self, **kwargs):
            yield {"event": "tool_start", "name": "kazanim_ara"}
            yield {"event": "tool_end", "name": "kazanim_ara", "ok": True, "ms": 40}
            yield {"event": "answer", "payload": {
                "answer": "cevap", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "meta": {"model": "gemini-3.7-flash", "degraded": []}}}

    monkeypatch.setattr(api, "_assistant_runtime", lambda: _Rt())

    res = client.post("/api/assistant/stream", json={"messages": [
        {"role": "user", "content": "kesir"}]})

    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("text/event-stream")
    body = res.get_data(as_text=True)
    assert "event: tool_start" in body
    assert "event: answer" in body
    assert body.rstrip().endswith("event: done\ndata: {}")


def test_assistant_stream_requires_auth(client_no_auth):
    res = client_no_auth.post("/api/assistant/stream", json={"messages": []})
    assert res.status_code in (401, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `TEST_AUTH_BYPASS=1 python -m pytest tests/test_dashboard_api.py -v -k stream`
Expected: FAIL — 404

- [ ] **Step 3: Add the endpoint**

`src/dashboard_api.py`:

```python
@app.route("/api/assistant/stream", methods=["POST"])
@require_auth
def assistant_stream():
    access = _require_assistant_access()
    if access is not None:
        return access

    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    session_id = str(data.get("session_id", ""))
    force_deep = bool(data.get("force_deep", False))

    def generate():
        try:
            runtime = _assistant_runtime()
            for event in runtime.chat_events(
                messages=messages, session_id=session_id, force_deep=force_deep
            ):
                name = event.pop("event")
                yield f"event: {name}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except AssistantUnavailableError:
            yield 'event: error\ndata: {"error":"assistant_unavailable"}\n\n'
        except Exception as exc:  # noqa: BLE001 — the stream must always close
            logger.error("assistant stream failed: %s", exc)
            yield f'event: error\ndata: {json.dumps({"error": str(exc)})}\n\n'
        yield "event: done\ndata: {}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})
```

`AssistantRuntime.chat_events()` ekle — `chat()`'i sarar, araç olaylarını yayınlar:

```python
    def chat_events(self, **kwargs: Any) -> "Iterator[dict[str, Any]]":
        """chat(), but announcing each tool as it runs.

        The tool loop can hold the request open for several seconds. Saying
        which source is being consulted is both a trust signal and, for this
        reader, the visible-time cue the interface is meant to provide.
        """
        events: list[dict[str, Any]] = []

        original = self.registry.dispatch

        def announcing(name: str, args: dict[str, Any]) -> Any:
            events.append({"event": "tool_start", "name": name})
            outcome = original(name, args)
            events.append({"event": "tool_end", "name": name,
                           "ok": bool(outcome.ok)})
            return outcome

        self.registry.dispatch = announcing  # type: ignore[method-assign]
        try:
            payload = self.chat(**kwargs)
        finally:
            self.registry.dispatch = original  # type: ignore[method-assign]

        yield from events
        yield {"event": "answer", "payload": payload}
```

**Not:** Bu sürüm araç olaylarını cevaptan *sonra* yayınlar; gerçek zamanlı akış için `chat()`'in bir kuyruk üzerinden çalışması gerekir. İlk teslimatta olay sırası doğrudur ve arayüz aşamaları gösterebilir; gerçek zamanlı yayın gerekiyorsa `queue.Queue` + worker thread'e geçilir. Bunu şimdi yapma — ölçülmüş bir ihtiyaç yok.

- [ ] **Step 4: Run test to verify it passes**

Run: `TEST_AUTH_BYPASS=1 python -m pytest tests/test_dashboard_api.py -v -k stream`
Expected: 2 passed

- [ ] **Step 5: Switch gunicorn to threaded workers**

`~/.config/systemd/user/ted-dashboard.service` içinde `--workers 2` satırından sonra ekle:

```
    --worker-class gthread \
    --threads 4 \
```

Uygula ve doğrula:

```bash
systemctl --user daemon-reload
systemctl --user restart ted-dashboard
systemctl --user status ted-dashboard --no-pager | head -20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8085/api/health
```
Expected: servis `active (running)`, health `200`.

Sync worker'la kalınırsa tek bir akış iki worker'dan birini kilitler ve ikinci istek dashboard'u durdurur.

- [ ] **Step 6: Wire the frontend to the stream**

`AssistantChat.tsx`: `WAITING_MESSAGES` dizisini sil, yerine araç etiketlerini koy ve `submit()`'e akış yolunu ekle.

```tsx
/** Read an SSE body and hand each event to the caller. */
async function readEventStream(
  res: Response,
  onEvent: (name: string, data: Record<string, unknown>) => void,
): Promise<void> {
  const reader = res.body?.getReader()
  if (!reader) throw new Error('akış gövdesi yok')
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // Frames are separated by a blank line; keep the trailing partial frame.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      let name = 'message'
      let payload = '{}'
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) name = line.slice(7).trim()
        else if (line.startsWith('data: ')) payload = line.slice(6)
      }
      try {
        onEvent(name, JSON.parse(payload))
      } catch {
        // A malformed frame must not kill the stream.
      }
    }
  }
}
```

**Ön-uçuş kararı (BULGU D).** Mevcut `submit()` `credentials: 'include'` gönderiyor —
oturum çerezi oradan geçiyor. Akış `fetch`'i onsuz yazılırsa `/api/assistant/stream`
401 döner, her istek sessizce yedek yola düşer ve özellik ölü doğduğu halde çalışıyor
görünür. Ayrıca `sessionId` diye bir değişken yok; kod bugün literal
`'dashboard-default'` gönderiyor. Aşağıdaki gövde ikisini de doğru yapar.

`submit()` içinde, mevcut `fetch('/api/assistant/chat', …)` çağrısını şununla sar:

```tsx
    setStage(null)
    try {
      const res = await fetch('/api/assistant/stream', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'dashboard-default',
          context_filters: {},
          messages: toApiMessages([...messages, userMsg]),
          force_deep: opts?.deep ?? false,
        }),
      })
      if (!res.ok || !res.body) throw new Error(`akış açılamadı (${res.status})`)

      let answered = false
      await readEventStream(res, (name, data) => {
        if (name === 'tool_start') {
          setStage(TOOL_LABEL[String(data.name)] ?? 'Kaynaklar taranıyor')
        } else if (name === 'answer') {
          answered = true
          appendAssistantMessage(data.payload as AssistantResponse)
        } else if (name === 'error') {
          throw new Error(String(data.error ?? 'akış hatası'))
        }
      })
      if (!answered) throw new Error('akış yanıtsız kapandı')
    } catch (streamErr) {
      // The non-streaming endpoint stays in place precisely for this: a proxy
      // that buffers SSE, or an older worker, must not cost the user an answer.
      console.warn('akış başarısız, klasik uca düşülüyor:', streamErr)
      const endpoint = mode === 'plan' ? '/api/assistant/plan' : '/api/assistant/chat'
      const res = await fetch(endpoint, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'dashboard-default',
          context_filters: {},
          messages: toApiMessages([...messages, userMsg]),
          force_deep: opts?.deep ?? false,
        }),
      })
      const data = await parseJsonSafe(res)
      if ('error' in data) throw new Error(data.error)
      appendAssistantMessage(data as AssistantResponse)
    } finally {
      setStage(null)
      setLoading(false)
    }
```

`const [stage, setStage] = useState<string | null>(null)` ekle ve `ThinkingIndicator`'a `stage` prop'u geçir; `stage` doluysa dönen `WAITING_MESSAGES` yerine onu göster. `appendAssistantMessage(payload)`, bugün `submit()` içinde inline yapılan mesaj ekleme işini (içerik, `citations`, `safetyFlags`, `planBlocks`, yeni `degraded`) tek yerde toplayan yardımcıdır.

Araç etiketleri:

```tsx
const TOOL_LABEL: Record<string, string> = {
  ogrenci_verisi_ara: 'Okul verilerin taranıyor',
  kazanim_ara: 'MEB kazanımları aranıyor',
  kazanim_listele: 'Kazanım listesi alınıyor',
  mufredat_ara: 'Müfredat aranıyor',
  kitap_listele: 'Ders kitapları listeleniyor',
  kitap_sayfa: 'Ders kitabı sayfası okunuyor',
  figur_ara: 'Görsel aranıyor',
  figur_getir: 'Görsel getiriliyor',
  oer_ara: 'Açık kaynaklar taranıyor',
  oer_kazanima_gore: 'Kazanıma bağlı kaynaklar alınıyor',
}
```

Akış başarısız olursa mevcut `/api/assistant/chat` ucuna düş — o uç kaldırılmıyor.

- [ ] **Step 7: Verify the stream is actually the path taken**

Yedek yol her hatayı yuttuğu için "çalışıyor görünmek" ile "çalışmak" burada ayrılmıyor.
Akışın gerçekten kullanıldığını kanıtla:

```bash
cd dashboard && npm run build && npx playwright test assistant-chat
```
Expected: PASS (bu spec'ler `/api/assistant/chat` yedeğini kullanmayı sürdürür).

Sonra tarayıcıda, oturum açıkken bir soru sor ve sunucu günlüğünde akış ucunun
vurulduğunu doğrula:

```bash
journalctl --user -u ted-dashboard -n 50 --no-pager | grep "assistant/stream"
```
Expected: en az bir `POST /api/assistant/stream` **200** satırı. `401` görürsen
`credentials: 'include'` eksiktir; hiç satır yoksa istemci akış yolunu hiç denemiyordur.
İkisi de bu task'ın başarısızlığıdır — yedek yolun cevap üretiyor olması yeterli değildir.

- [ ] **Step 8: Commit**

```bash
git add src/dashboard_api.py src/assistant_core.py dashboard/src/components/AssistantChat.tsx tests/test_dashboard_api.py
git commit -m "feat: stream the assistant's progress while it consults sources

The tool loop can hold a request open for several seconds behind a spinner
that says nothing. The stream names each source as it is consulted, which is
the visible-time cue this interface is supposed to give its reader.

gunicorn moves to threaded workers in the same change: with two sync workers a
single stream would pin one of them and a second request would stall the
dashboard."
```

---

## Task 12: Go-live dokümanını gerçeğe döndür

**Files:**
- Modify: `docs/assistant-go-live.md`

**Interfaces:**
- Consumes: Task 1–11'in tamamı
- Produces: yok (doküman)

- [ ] **Step 1: Rewrite the runbook**

`docs/assistant-go-live.md` şu an Ollama dönemini anlatıyor: `ollama pull mxbai-embed-large`, `ASSISTANT_CHAT_MODEL=qwen2.5-coder:7b`. Kod Gemini'ye geçtiğinde güncellenmemiş. Şunları içerecek şekilde yeniden yaz:

- **Önkoşullar:** `GEMINI_API_KEY`, `MUFREDAT_MCP_API_KEY`, `EGITIM_KAYNAK_MCP_API_KEY`, `DASHBOARD_SECRET_KEY`, `ASSISTANT_API_KEY`. Ollama yalnız gömme (embedding) indeksi için gerekli; sohbet yolu onu kullanmıyor.

- **DAĞITIM TUZAĞI — bu adım atlanırsa özellik sessizce ölür.** Servis
  (`~/.config/systemd/user/ted-dashboard.service`) ortamını `EnvironmentFile=.env`'den
  alıyor. İki MCP anahtarı geliştirme makinesinde **interaktif kabuk ortamında** duruyor
  ama **`.env` içinde değil**. Bu haliyle gunicorn onları göremez: kayıt defteri sıfır
  müfredat aracıyla açılır, asistan yalnız yerel dosyalardan cevap verir ve **sağlıklı
  görünür**. Task 3'ün düzeltmesinden sonra `degraded()` bunu bildirir ve arayüzde rozet
  yanar, ama rozet arızayı görünür kılar — gidermez.

  Dağıtımdan önce iki anahtarı `.env`'e ekle (dosya zaten mod 600 ve gitignore'lu) ve
  doğrula:

  ```bash
  systemctl --user restart ted-dashboard
  python -c "
  from src.assistant_tools import build_registry
  reg = build_registry(lambda q,k: [])
  print('araçlar:', len(reg.declarations()), '| degraded:', reg.degraded())
  "
  ```
  Beklenen: `araçlar: 10 | degraded: []`. `degraded` boş değilse veya araç sayısı 1
  (yalnız `ogrenci_verisi_ara`) ise anahtarlar servise ulaşmıyordur.
- **MCP sağlık kontrolü:**
  ```bash
  python -c "
  import os; from src.assistant_tools import build_registry
  reg = build_registry(lambda q,k: [])
  print('araçlar:', [d['name'] for d in reg.declarations()])
  print('degraded:', reg.degraded())
  "
  ```
  Beklenen: 10 araç adı, boş `degraded`.
- **Model zinciri kontrolü:** `python -c "from src.assistant_core import GeminiClient; print(GeminiClient.FAST_MODELS, GeminiClient.DEEP_MODELS)"`
- **Servis:** `--worker-class gthread --threads 4` gerekliliği ve gerekçesi.
- **Degradasyon beklentisi:** MCP anahtarı yoksa asistan çalışmaya devam eder, yalnız okul verisiyle yanıt verir ve arayüzde rozet gösterir. Bu bir arıza değil, tasarlanmış davranıştır.
- Ollama'ya ait `ollama pull` ve `ASSISTANT_OLLAMA_*` bölümlerini sil.

- [ ] **Step 2: Verify the commands in the doc actually run**

Dokümandaki her komutu sırayla çalıştır. Çalışmayan komut dokümanda kalmaz.

- [ ] **Step 3: Commit**

```bash
git add docs/assistant-go-live.md
git commit -m "docs: bring the assistant runbook back in line with the code

The runbook still walked through pulling Ollama models and setting
ASSISTANT_CHAT_MODEL, neither of which the chat path has touched since it
moved to Gemini. It now covers the keys that are actually required, how to
check the MCP fleet, and why the service needs threaded workers."
```

---

## Kabul kriterleri

Tamamlandığında hepsi doğrulanabilir olmalı:

- [ ] `python -m pytest tests/ -v` — tamamı geçiyor
- [ ] `cd dashboard && npm run build && npm run lint` — temiz
- [ ] `npx playwright test assistant-chat` — geçiyor
- [ ] `GeminiClient.FAST_MODELS + DEEP_MODELS` içinde `gemini-2.0-*` yok
- [ ] `grep -c "cds-ai-\|ai-aura\|ai-border\|ai-popover" dashboard/src/components/AssistantChat.scss` ≥ 16
- [ ] `grep -c "stripInlineCitations" dashboard/src/components/AssistantChat.tsx` = 0
- [ ] `grep -c "#edf5ff\|#0f62fe" dashboard/src/components/AssistantChat.scss` = 0
- [ ] "6. sınıf fen kuvvet kazanımları" sorusu `kazanim_ara`'yı çağırıyor ve `kind: "mufredat"` atıf döndürüyor
- [ ] MCP anahtarları kaldırıldığında asistan çalışmaya devam ediyor ve degradasyon rozeti gösteriyor
- [ ] `systemctl --user status ted-dashboard` → `active (running)`, `gthread` worker'la
