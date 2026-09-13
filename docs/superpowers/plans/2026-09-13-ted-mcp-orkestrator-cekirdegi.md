# ted-mcp orkestratör çekirdeği — Uygulama Planı (alt proje 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TED deposunda, dört web yüzeyinin (claude.ai, Codex, Grok, Gemini Spark) Google girişli OAuth 2.1 ile bağlanabildiği ayrı bir ASGI MCP süreci (`ted-mcp`) kurmak; ilk beş aracı (`edupedia_durum`, `edupedia_rehber`, `edupedia_baglam`, `edupedia_kapsam`, `edupedia_kaynak_oku`) ağsız testlerle teslim etmek.

**Architecture:** `src/mcp_server/` altında `mcp` SDK 1.28.1 FastMCP (stateless streamable HTTP) + Starlette. Kimlik katmanı egitim-kaynak'ın kanıtlanmış OAuth kalıbını izler; tek fark, onay adımının Google Sign-In + `src/roles.py` aile listesi olması ve token'ların e-postaya bağlanmasıdır. İş mantığı FastMCP'den bağımsız `Tools` sınıfındadır; yan filo `src/mcp_client.py` ile, TED bağlamı dashboard'un loopback API'siyle okunur.

**Tech Stack:** Python 3.12.3 (TED `.venv`), mcp 1.28.1, starlette 1.3.1, sse-starlette 3.4.5, uvicorn 0.51.0, python-multipart 0.0.32, httpx 0.28.1 (yalnız test istemcisi), requests, google-auth, pytest.

**Spec:** `docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md` (onaylı; §12b plan güncellemeleri dahil).

## Global Constraints

- Kod yorumları **İngilizce**; kullanıcıya dönen metin ve alan adları **Türkçe** (TED konvansiyonu).
- `src/dashboard_api.py` **import edilmez** (import sırasında `os.chdir`, `load_env`, `DASHBOARD_SECRET_KEY` yoksa `RuntimeError`, Flask `app` kurulumu).
- Roller tek kaynak: `src/roles.py`. `reader` rol hiçbir MCP aracına ve OAuth onayına erişemez; yalnız `full`.
- Yalnız araç sunulur (MCP prompt/resource yok). Büyük içerik (HTML, görsel baytı, tam kitap sayfası) araç yanıtıyla modele dönmez.
- Her araç yanıtı `mcp_verified: false` taşır; getirim yapan araçlar `coverage` manifestosu taşır: sunucu başına `hit` | `empty` | `degraded:<neden>` | `skipped:<neden>`.
- PKCE yalnız **S256**. Yetkilendirme kodu tek kullanımlık, **5 dk**. Erişim token'ı **1 saat**; yenileme token'ı **30 gün**, her kullanımda döner, tekrar kullanımda aile iptal edilir. Depolama `output/ted_mcp_oauth.sqlite3`, yalnız SHA-256 hash.
- Statik yedek anahtar öneki `tdyM_`; dashboard `tdyK_` anahtarları MCP'de **geçmez**.
- `redirect_uri` izin listesi: `https://claude.ai`, `https://claude.com`, `https://chatgpt.com`, `https://grok.com`, `https://oauth-redirect.googleusercontent.com`, `https://vscode.dev`, `https://insiders.vscode.dev`, loopback (`localhost`/`127.0.0.1`/`::1`) herhangi portta; origin tam eşleşmesi (lookalike reddi).
- CORS en dışta; `Access-Control-Expose-Headers` `mcp-session-id, www-authenticate` içerir. 401 `WWW-Authenticate: Bearer realm="ted-mcp", resource_metadata="<base>/.well-known/oauth-protected-resource"`.
- anamnesis koleksiyonu `edupedia:run:<run_id>`, `doc_id` `edupedia:<run_id>:<kanonik>` ve **≤ 56 bayt**; `run_id` 12 hex.
- Çağrı başına zaman aşımı 25 sn (`McpClient` varsayılanı); dashboard loopback çağrısı 10 sn.
- Tüm testler ağsız geçer: `unshare -rn .venv/bin/python -m pytest -q`.
- Paket kurulumu **`.venv/bin/python -m pip`** ile yapılır (`.venv/bin/pip` shebang'i eski `/mnt/pi-shared` yoluna işaret ediyor).
- Commit'ler yalnız ilgili dosyaları stage eder; `.env`, `output/`, kimlik bilgisi dosyaları asla stage edilmez; push yok.
- Commit mesajı sonu: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Dosya Haritası

| Dosya | Sorumluluk |
|---|---|
| `src/roles.py` (yeni) | Aile listesi, roller, `GOOGLE_CLIENT_ID`, `role_of()`, `is_full()` |
| `src/dashboard_api.py` (değişir) | Rolleri `src.roles`'tan import eder |
| `requirements.txt` (değişir) | MCP bağımlılıkları (sabit sürüm) |
| `src/mcp_server/__init__.py` | `__version__` |
| `src/mcp_server/vendor_sync.py` | edupedia varlıklarını kopyala + `PROVENANCE.json` |
| `src/mcp_server/vendor/` | Vendored `SKILL.md`, `assets/module-template.html`, `scripts/validate_module.py`, `references/*.md`, `PROVENANCE.json` |
| `src/mcp_server/gates.py` | Vendored doğrulayıcıyı modül olarak yükle, `gate_count()`, `run_gates()` |
| `src/mcp_server/config.py` | Ortam değişkenlerinden `Settings` |
| `src/mcp_server/coverage.py` | Kapsam manifestosu |
| `src/mcp_server/federation.py` | Yan filo istemci kayıt defteri + JSON araç çağrısı |
| `src/mcp_server/oauth_redirect.py` | `redirect_uri` izin listesi (egitim-kaynak kalıbı) |
| `src/mcp_server/oauth_store.py` | SQLite: kod, erişim/yenileme token'ı, `tdyM_` anahtarı |
| `src/mcp_server/keys.py` | `tdyM_` anahtar CLI'si |
| `src/mcp_server/google_identity.py` | Google `id_token` doğrulama (enjekte edilebilir) |
| `src/mcp_server/http_app.py` | Starlette uygulaması: CORS, host denetimi, Bearer kapısı, PRM/AS metadata, `/oauth/*`, `/health`, MCP mount, `main()` |
| `src/mcp_server/server.py` | FastMCP kurulumu + araç sarmalayıcıları + kimlik çözümü |
| `src/mcp_server/tools.py` | `Tools` iş mantığı sınıfı |
| `src/mcp_server/rehber.py` | Rehber bölümleri (vendored referanslardan) |
| `src/mcp_server/dashboard_context.py` | Dashboard loopback API istemcisi → yaklaşan sınav/ödev |
| `src/mcp_server/runs.py` | Çalıştırma kaydı (`output/edupedia_runs/<run_id>/`) |
| `src/mcp_server/kapsam.py` | Müfredat doğrulama + kitap + figür + OER + anamnesis alımı |
| `src/mcp_server/kaynak_oku.py` | anamnesis `hybrid_query` + yerel BM25 yedeği |
| `tests/test_roles.py`, `tests/test_mcp_*.py` | Testler (TED düz `tests/test_*.py` düzeni) |

---

### Task 1: MCP bağımlılıkları ve `src/roles.py` çıkarımı

**Files:**
- Create: `src/roles.py`
- Modify: `src/dashboard_api.py:28` (import ekle) ve `src/dashboard_api.py:111-129` (tanımları kaldır)
- Modify: `requirements.txt`
- Test: `tests/test_roles.py`

**Interfaces:**
- Produces: `src.roles.GOOGLE_CLIENT_ID: str`, `ROLE_FULL = "full"`, `ROLE_READER = "reader"`, `USER_ROLES: dict[str, str]`, `ALLOWED_EMAILS: set[str]`, `FULL_ACCESS_EMAILS: set[str]`, `role_of(email: str | None) -> str | None`, `is_full(email: str | None) -> bool`.

- [ ] **Step 1: Write the failing test**

`tests/test_roles.py`:

```python
"""Roster extraction: one source of roles for the dashboard and ted-mcp."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_role_of_known_and_unknown_emails():
    from src import roles

    assert roles.role_of("drmahirkurt@gmail.com") == roles.ROLE_FULL
    assert roles.role_of("murzogluhulya@gmail.com") == roles.ROLE_READER
    assert roles.role_of("stranger@example.com") is None
    assert roles.role_of(None) is None
    assert roles.role_of("") is None


def test_role_of_normalises_case_and_whitespace():
    from src import roles

    assert roles.role_of("  DrMahirKurt@Gmail.com ") == roles.ROLE_FULL


def test_is_full_only_for_full_role():
    from src import roles

    assert roles.is_full("isikkurtx@gmail.com") is True
    assert roles.is_full("mahirkurtmd@gmail.com") is False
    assert roles.is_full("stranger@example.com") is False


def test_derived_sets_match_roster():
    from src import roles

    assert roles.ALLOWED_EMAILS == set(roles.USER_ROLES)
    assert roles.FULL_ACCESS_EMAILS == {
        e for e, r in roles.USER_ROLES.items() if r == roles.ROLE_FULL
    }


def test_dashboard_reexports_the_same_objects(monkeypatch):
    monkeypatch.setenv("TEST_AUTH_BYPASS", "1")
    monkeypatch.setenv("DASHBOARD_SECRET_KEY", os.environ.get("DASHBOARD_SECRET_KEY") or "test-secret")
    from src import dashboard_api, roles

    assert dashboard_api.USER_ROLES is roles.USER_ROLES
    assert dashboard_api.ALLOWED_EMAILS is roles.ALLOWED_EMAILS
    assert dashboard_api.FULL_ACCESS_EMAILS is roles.FULL_ACCESS_EMAILS
    assert dashboard_api.GOOGLE_CLIENT_ID == roles.GOOGLE_CLIENT_ID
    assert dashboard_api.ROLE_FULL == roles.ROLE_FULL


def test_importing_roles_does_not_pull_in_flask():
    code = "import sys; import src.roles; print('flask' in sys.modules)"
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_roles.py -v`
Expected: FAIL — `ImportError: cannot import name 'roles' from 'src'` (veya `ModuleNotFoundError: No module named 'src.roles'`).

- [ ] **Step 3: Create `src/roles.py`**

```python
"""Household roster: the single source of who may use TEDY and with which role.

Two processes import this module: the Flask dashboard (src/dashboard_api.py) and the
MCP orchestrator (src/mcp_server). The orchestrator cannot import src.dashboard_api,
because that import chdirs, loads .env, requires DASHBOARD_SECRET_KEY and builds the
Flask app as side effects.
"""
from __future__ import annotations

GOOGLE_CLIENT_ID = "343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com"

# "full"   — the household dashboard: every page and every endpoint.
# "reader" — Tedy Books only. Nothing else about Işık's school life is visible.
ROLE_FULL = "full"
ROLE_READER = "reader"

USER_ROLES = {
    "isikkurtx@gmail.com": ROLE_FULL,
    "drmahirkurt@gmail.com": ROLE_FULL,
    "ozlem.murzoglu@gmail.com": ROLE_FULL,
    "huriye.murzoglu@gmail.com": ROLE_FULL,
    "murzogluhulya@gmail.com": ROLE_READER,
    "mahirkurtmd@gmail.com": ROLE_READER,
}

ALLOWED_EMAILS = set(USER_ROLES)
FULL_ACCESS_EMAILS = {e for e, r in USER_ROLES.items() if r == ROLE_FULL}


def role_of(email: str | None) -> str | None:
    """Role for an email, or None when the address is not on the roster."""
    if not email:
        return None
    return USER_ROLES.get(email.strip().lower())


def is_full(email: str | None) -> bool:
    """True only for roster members with the full role."""
    return role_of(email) == ROLE_FULL
```

- [ ] **Step 4: Point `src/dashboard_api.py` at `src.roles`**

Insert after line 28 (`from src.course_names import normalize_course`):

```python
from src.roles import (  # noqa: F401  (re-exported: tests read dashboard_api.USER_ROLES etc.)
    ALLOWED_EMAILS,
    FULL_ACCESS_EMAILS,
    GOOGLE_CLIENT_ID,
    ROLE_FULL,
    ROLE_READER,
    USER_ROLES,
)
```

Then delete this exact block (currently lines 111-129), leaving `READER_ENDPOINTS` and everything after it untouched:

```python
GOOGLE_CLIENT_ID = "343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com"

# --- Roles ---
# "full"   — the household dashboard: every page and every endpoint.
# "reader" — Tedy Books only. Nothing else about Işık's school life is visible.
ROLE_FULL = "full"
ROLE_READER = "reader"

USER_ROLES = {
    "isikkurtx@gmail.com": ROLE_FULL,
    "drmahirkurt@gmail.com": ROLE_FULL,
    "ozlem.murzoglu@gmail.com": ROLE_FULL,
    "huriye.murzoglu@gmail.com": ROLE_FULL,
    "murzogluhulya@gmail.com": ROLE_READER,
    "mahirkurtmd@gmail.com": ROLE_READER,
}

ALLOWED_EMAILS = set(USER_ROLES)
FULL_ACCESS_EMAILS = {e for e, r in USER_ROLES.items() if r == ROLE_FULL}
```

Replace it with a single comment line so the section stays readable:

```python
# --- Roles: defined in src/roles.py (shared with the ted-mcp orchestrator) ---
```

- [ ] **Step 5: Add MCP dependencies**

Append to `requirements.txt` (pins match the fleet's proven egitim-kaynak lock):

```
mcp==1.28.1
starlette==1.3.1
sse-starlette==3.4.5
uvicorn==0.51.0
python-multipart==0.0.32
httpx==0.28.1
```

Run: `.venv/bin/python -m pip install -r requirements.txt`
Then: `.venv/bin/python -c "import mcp, starlette, uvicorn, multipart; from mcp.server.fastmcp import FastMCP; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_roles.py tests/test_dashboard_api.py tests/test_reader_role.py -q`
Expected: all PASS (roles tests + the existing dashboard and reader-role suites unchanged).

- [ ] **Step 7: Commit**

```bash
git add src/roles.py src/dashboard_api.py requirements.txt tests/test_roles.py
git commit -m "refactor(roles): aile listesini src/roles.py'ye taşı, MCP bağımlılıklarını ekle

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 2: edupedia varlıklarının vendoring'i ve kapı yükleyicisi

**Files:**
- Create: `src/mcp_server/__init__.py`
- Create: `src/mcp_server/vendor_sync.py`
- Create: `src/mcp_server/gates.py`
- Create (üretilir): `src/mcp_server/vendor/SKILL.md`, `src/mcp_server/vendor/assets/module-template.html`, `src/mcp_server/vendor/scripts/validate_module.py`, `src/mcp_server/vendor/references/*.md` (17 dosya), `src/mcp_server/vendor/PROVENANCE.json`
- Test: `tests/test_mcp_vendor.py`

**Interfaces:**
- Produces: `src.mcp_server.__version__ = "0.1.0"`; `vendor_sync.VENDOR_DIR: Path`; `vendor_sync.sync(source: Path, vendor: Path = VENDOR_DIR) -> dict`; `vendor_sync.check(source: Path, vendor: Path = VENDOR_DIR) -> list[str]`; `vendor_sync.load_provenance(vendor: Path = VENDOR_DIR) -> dict`; `gates.GATE_FUNCTION_NAMES: tuple[str, ...]` (16 ad); `gates.gate_count() -> int`; `gates.run_gates(html: str) -> dict[str, dict]`.

Olgular: vendored doğrulayıcının dosya bağımlılığı yoktur (yalnız verilen HTML'i okur, `if __name__ == "__main__"` korumalı). Şablonun kendi demo modülü bugün 13 PASS + 3 SKIPPED (G-CURRICULUM, G-VERIFY, G-EXAM), FAIL yok.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_vendor.py`:

```python
"""Vendored edupedia assets: provenance pins, template and gate loader."""
import hashlib
import json
from pathlib import Path

import pytest

from src.mcp_server import gates, vendor_sync

SOURCE = Path("/mnt/thunderbolt/workspaces/CureoPrivate/plugins/edupedia/skills/carbon-edupedia")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_provenance_lists_required_files():
    prov = vendor_sync.load_provenance()
    for rel in ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py"):
        assert rel in prov["files"]
    refs = [r for r in prov["files"] if r.startswith("references/")]
    assert len(refs) == 17
    assert prov["source_root"]


def test_every_vendored_file_matches_its_pinned_sha256():
    prov = vendor_sync.load_provenance()
    for rel, digest in prov["files"].items():
        path = vendor_sync.VENDOR_DIR / rel
        assert path.is_file(), rel
        assert _sha(path) == digest, rel


def test_no_unpinned_files_in_vendor_dir():
    prov = vendor_sync.load_provenance()
    on_disk = {
        str(p.relative_to(vendor_sync.VENDOR_DIR))
        for p in vendor_sync.VENDOR_DIR.rglob("*")
        if p.is_file() and p.name != "PROVENANCE.json" and "__pycache__" not in p.parts
    }
    assert on_disk == set(prov["files"])


def test_template_carries_module_data_placeholder():
    html = (vendor_sync.VENDOR_DIR / "assets" / "module-template.html").read_text(encoding="utf-8")
    assert "const MODULE_DATA = {" in html


def test_gate_loader_exposes_sixteen_gates():
    assert gates.gate_count() == 16
    vm = gates.validator()
    for name in gates.GATE_FUNCTION_NAMES:
        assert callable(getattr(vm, name)), name


def test_vendored_template_demo_has_no_failing_gate():
    html = (vendor_sync.VENDOR_DIR / "assets" / "module-template.html").read_text(encoding="utf-8")
    report = gates.run_gates(html)
    assert len(report) == 16
    assert not [g for g, v in report.items() if v["status"] == "FAIL"]
    assert sum(1 for v in report.values() if v["status"] == "PASS") >= 13


def test_run_gates_reports_failures_on_broken_html():
    report = gates.run_gates("<html><body><p>emoji 🎉</p></body></html>")
    assert any(v["status"] == "FAIL" for v in report.values())


def test_sync_then_check_round_trip(tmp_path):
    src = tmp_path / "src"
    for rel in ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py", "references/a.md"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(f"content of {rel}\n", encoding="utf-8")
    vendor = tmp_path / "vendor"
    (vendor / "references").mkdir(parents=True)
    (vendor / "references" / "stale.md").write_text("old\n", encoding="utf-8")

    prov = vendor_sync.sync(src, vendor)

    assert set(prov["files"]) == {"SKILL.md", "assets/module-template.html", "scripts/validate_module.py", "references/a.md"}
    assert not (vendor / "references" / "stale.md").exists()
    assert vendor_sync.check(src, vendor) == []
    (src / "references" / "a.md").write_text("changed\n", encoding="utf-8")
    assert vendor_sync.check(src, vendor) == ["drift: references/a.md"]


@pytest.mark.skipif(not SOURCE.is_dir(), reason="CureoPrivate checkout not present")
def test_vendor_matches_live_plugin_source():
    assert vendor_sync.check(SOURCE) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_vendor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mcp_server'`.

- [ ] **Step 3: Create `src/mcp_server/__init__.py`**

```python
"""ted-mcp: the edupedia orchestrator served from TEDY (spec 2026-09-13)."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Create `src/mcp_server/vendor_sync.py`**

```python
"""Copy edupedia authoring assets into src/mcp_server/vendor/ and pin their provenance.

ted-mcp is the runtime authority for the module template, the MODULE_DATA schema
reference and the quality gates (spec §5.2). This tool is the only way those files
change: it copies them from the CureoPrivate edupedia skill and writes PROVENANCE.json
(source commit + sha256 per file). tests/test_mcp_vendor.py pins the result.

Usage:
    .venv/bin/python -m src.mcp_server.vendor_sync            # sync from the default source
    .venv/bin/python -m src.mcp_server.vendor_sync --check    # exit 1 on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
DEFAULT_SOURCE = Path("/mnt/thunderbolt/workspaces/CureoPrivate/plugins/edupedia/skills/carbon-edupedia")
FIXED_FILES = ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py")
PROVENANCE_NAME = "PROVENANCE.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_files(source: Path) -> list[str]:
    refs = sorted(str(p.relative_to(source)) for p in (source / "references").glob("*.md"))
    rels = [*FIXED_FILES, *refs]
    missing = [rel for rel in rels if not (source / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"missing in source {source}: {', '.join(missing)}")
    return rels


def _git_commit(source: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def load_provenance(vendor: Path = VENDOR_DIR) -> dict:
    return json.loads((vendor / PROVENANCE_NAME).read_text(encoding="utf-8"))


def sync(source: Path, vendor: Path = VENDOR_DIR) -> dict:
    """Copy every source file, drop vendored files no longer in the source, write provenance."""
    rels = _source_files(source)
    wanted = set(rels)
    if vendor.is_dir():
        for path in sorted(vendor.rglob("*")):
            if not path.is_file() or path.name == PROVENANCE_NAME or "__pycache__" in path.parts:
                continue
            if str(path.relative_to(vendor)) not in wanted:
                path.unlink()
    files: dict[str, str] = {}
    for rel in rels:
        dst = vendor / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, dst)
        files[rel] = _sha256(dst)
    provenance = {
        "source_root": str(source),
        "source_commit": _git_commit(source),
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    (vendor / PROVENANCE_NAME).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return provenance


def check(source: Path, vendor: Path = VENDOR_DIR) -> list[str]:
    """Drift messages between source and vendor; an empty list means identical."""
    pinned = load_provenance(vendor)["files"]
    rels = _source_files(source)
    problems = [f"missing in vendor: {rel}" for rel in rels if rel not in pinned]
    problems += [f"removed upstream: {rel}" for rel in pinned if rel not in rels]
    problems += [
        f"drift: {rel}" for rel in rels if rel in pinned and _sha256(source / rel) != pinned[rel]
    ]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true", help="report drift, do not copy")
    args = parser.parse_args(argv)
    if args.check:
        problems = check(args.source)
        for line in problems:
            print(line)
        return 1 if problems else 0
    provenance = sync(args.source)
    print(f"vendored {len(provenance['files'])} files from {provenance['source_commit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Create `src/mcp_server/gates.py`**

```python
"""Load the vendored edupedia quality gates as a module and run them."""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"

# Order mirrors the retired edupedia_site runner (_GATE_FUNCS), 16 gates.
GATE_FUNCTION_NAMES = (
    "gate_emoji",
    "gate_carbon",
    "gate_a11y",
    "gate_interact",
    "gate_selfcontained",
    "gate_contrast",
    "gate_wellbeing",
    "gate_voice",
    "gate_svg",
    "gate_audio",
    "gate_token_authority",
    "gate_curriculum",
    "gate_verify",
    "gate_flow",
    "gate_carbon_grid",
    "gate_exam",
)


@lru_cache(maxsize=1)
def validator() -> ModuleType:
    path = VENDOR_DIR / "scripts" / "validate_module.py"
    spec = importlib.util.spec_from_file_location("ted_mcp_vendor_validate_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load vendored validator at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gate_count() -> int:
    return len(GATE_FUNCTION_NAMES)


def run_gates(html: str) -> dict[str, dict[str, Any]]:
    """Run every gate; return {gate_id: {"status": PASS|WARN|FAIL|SKIPPED, ...}}."""
    vm = validator()
    result = vm.Result()
    for name in GATE_FUNCTION_NAMES:
        getattr(vm, name)(html, result)
    return result.to_json_gates()
```

- [ ] **Step 6: Vendor the assets**

Run: `.venv/bin/python -m src.mcp_server.vendor_sync`
Expected: `vendored 20 files from <40-hex commit>`

Run: `.venv/bin/python -m src.mcp_server.vendor_sync --check; echo "rc=$?"`
Expected: `rc=0` (no output lines).

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_vendor.py -v`
Expected: 9 PASS (the live-source test runs because the CureoPrivate checkout exists on this host).

- [ ] **Step 8: Commit**

```bash
git add src/mcp_server/__init__.py src/mcp_server/vendor_sync.py src/mcp_server/gates.py src/mcp_server/vendor tests/test_mcp_vendor.py
git commit -m "feat(ted-mcp): edupedia şablonu, referanslar ve 16 kapıyı PROVENANCE ile vendorla

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 3: Yapılandırma, kapsam manifestosu ve federasyon katmanı

**Files:**
- Create: `src/mcp_server/config.py`
- Create: `src/mcp_server/coverage.py`
- Create: `src/mcp_server/federation.py`
- Test: `tests/test_mcp_federation.py`

**Interfaces:**
- Consumes: `src.mcp_client.McpClient(name, url, api_key, timeout=25.0, session=None)`, `McpClient.call_tool(name, arguments) -> McpToolResult(ok, text, images, error)`.
- Produces:
  - `config.Settings` (frozen dataclass): `public_base_url: str`, `allowed_hosts: tuple[str, ...]`, `data_dir: Path`, `oauth_db_path: Path`, `dashboard_api_url: str`, `dashboard_api_key: str`, `servers: dict[str, ServerConfig]`; `config.ServerConfig(name: str, url: str, api_key: str)`; `config.load_settings(env: Mapping[str, str] | None = None, project_root: Path | None = None) -> Settings`.
  - `coverage.Coverage` with `hit(server)`, `empty(server)`, `degraded(server, reason)`, `skipped(server, reason)`, `as_dict() -> dict[str, str]`.
  - `federation.FederationError(Exception)` with `.server`, `.tool`, `.reason`.
  - `federation.Federation(settings, client_factory=McpClient)`: `configured(server) -> bool`; `call(server, tool, args, beklenen: Literal["liste", "nesne"]) -> list | dict` (raises `FederationError`).
  - `federation.decode_json_stream(text: str) -> list[Any]`.
  - Server name constants: `MUFREDAT = "maarif-mufredat"`, `EGITIM_KAYNAK = "egitim-kaynak"`, `ANAMNESIS = "anamnesis"`.

Ölçülmüş olgu (2026-09-13, canlı): FastMCP liste dönüşünü **öğe başına ayrı metin bloğu** yapar, `McpClient` blokları `"\n"` ile birleştirir. Sonuç art arda girintili JSON nesneleridir; tek öğeli liste tek `dict` gibi, boş liste boş metin gibi görünür. Bu yüzden çağıran `beklenen` ile ne beklediğini söyler.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_federation.py`:

```python
"""Config loading, coverage manifest and the federation JSON decoding contract."""
import json
from pathlib import Path

import pytest

from src.mcp_client import McpToolResult
from src.mcp_server import config, coverage, federation


def _env(**over):
    base = {
        "TED_MCP_PUBLIC_BASE_URL": "https://mcp.tedy.online",
        "MUFREDAT_MCP_API_KEY": "k-muf",
        "EGITIM_KAYNAK_MCP_API_KEY": "k-egi",
        "ANAMNESIS_MCP_API_KEY": "",
        "TED_DASHBOARD_API_KEY": "tdyK_x",
    }
    base.update(over)
    return base


def test_load_settings_defaults(tmp_path):
    s = config.load_settings(_env(), project_root=tmp_path)
    assert s.public_base_url == "https://mcp.tedy.online"
    assert s.allowed_hosts == ("mcp.tedy.online",)
    assert s.data_dir == tmp_path / "output"
    assert s.oauth_db_path == tmp_path / "output" / "ted_mcp_oauth.sqlite3"
    assert s.dashboard_api_url == "http://127.0.0.1:8085"
    assert s.servers["maarif-mufredat"].url == "https://mufredat.cureonics.com/mcp"
    assert s.servers["egitim-kaynak"].api_key == "k-egi"
    assert s.servers["anamnesis"].url == "https://anamnesis-mcp.cureonics.workers.dev/mcp"


def test_load_settings_overrides_and_strips_trailing_slash(tmp_path):
    s = config.load_settings(
        _env(TED_MCP_PUBLIC_BASE_URL="https://x.example/", TED_MCP_ALLOWED_HOSTS="a.example, b.example"),
        project_root=tmp_path,
    )
    assert s.public_base_url == "https://x.example"
    assert s.allowed_hosts == ("a.example", "b.example")


def test_coverage_manifest_records_each_state():
    c = coverage.Coverage()
    c.hit("maarif-mufredat")
    c.empty("egitim-kaynak")
    c.degraded("anamnesis", "timeout")
    c.skipped("pexels", "alt proje 4")
    assert c.as_dict() == {
        "maarif-mufredat": "hit",
        "egitim-kaynak": "empty",
        "anamnesis": "degraded:timeout",
        "pexels": "skipped:alt proje 4",
    }


def test_decode_json_stream_handles_concatenated_pretty_objects():
    text = json.dumps({"a": 1}, indent=2) + "\n" + json.dumps({"b": 2}, indent=2)
    assert federation.decode_json_stream(text) == [{"a": 1}, {"b": 2}]
    assert federation.decode_json_stream("") == []
    assert federation.decode_json_stream("  \n ") == []


def test_decode_json_stream_rejects_garbage():
    with pytest.raises(ValueError):
        federation.decode_json_stream('{"a": 1} not-json')


class _FakeClient:
    calls = []

    def __init__(self, name, url, api_key, timeout=25.0, session=None):
        self.name = name

    def call_tool(self, name, arguments):
        _FakeClient.calls.append((self.name, name, arguments))
        return _FakeClient.responses[(self.name, name)]


def _fed(tmp_path, responses):
    _FakeClient.responses = responses
    _FakeClient.calls = []
    return federation.Federation(config.load_settings(_env(), project_root=tmp_path), client_factory=_FakeClient)


def test_call_liste_single_item_stays_a_list(tmp_path):
    item = {"slug": "fen-bilimleri-dersi"}
    fed = _fed(tmp_path, {("maarif-mufredat", "list_subjects"): McpToolResult(ok=True, text=json.dumps(item, indent=2))})
    assert fed.call("maarif-mufredat", "list_subjects", {"q": "fen"}, beklenen="liste") == [item]


def test_call_liste_empty_text_is_empty_list(tmp_path):
    fed = _fed(tmp_path, {("maarif-mufredat", "list_subjects"): McpToolResult(ok=True, text="")})
    assert fed.call("maarif-mufredat", "list_subjects", {}, beklenen="liste") == []


def test_call_nesne_requires_exactly_one_object(tmp_path):
    two = json.dumps({"a": 1}) + "\n" + json.dumps({"b": 2})
    fed = _fed(tmp_path, {
        ("maarif-mufredat", "search_learning_outcomes"): McpToolResult(ok=True, text=json.dumps({"results": []})),
        ("maarif-mufredat", "server_info"): McpToolResult(ok=True, text=two),
    })
    assert fed.call("maarif-mufredat", "search_learning_outcomes", {"q": "x"}, beklenen="nesne") == {"results": []}
    with pytest.raises(federation.FederationError) as exc:
        fed.call("maarif-mufredat", "server_info", {}, beklenen="nesne")
    assert exc.value.reason == "unexpected_shape"


def test_call_tool_error_raises_with_reason(tmp_path):
    fed = _fed(tmp_path, {("egitim-kaynak", "kb_search"): McpToolResult(ok=False, error="boom")})
    with pytest.raises(federation.FederationError) as exc:
        fed.call("egitim-kaynak", "kb_search", {"q": "x"}, beklenen="nesne")
    assert exc.value.server == "egitim-kaynak"
    assert exc.value.reason == "tool_error: boom"


def test_unconfigured_server_raises_without_calling(tmp_path):
    fed = _fed(tmp_path, {})
    assert fed.configured("anamnesis") is False
    with pytest.raises(federation.FederationError) as exc:
        fed.call("anamnesis", "hybrid_query", {}, beklenen="nesne")
    assert exc.value.reason == "not_configured"
    assert _FakeClient.calls == []


def test_clients_are_reused_per_server(tmp_path):
    fed = _fed(tmp_path, {("maarif-mufredat", "list_subjects"): McpToolResult(ok=True, text="")})
    fed.call("maarif-mufredat", "list_subjects", {}, beklenen="liste")
    fed.call("maarif-mufredat", "list_subjects", {}, beklenen="liste")
    assert fed._client("maarif-mufredat") is fed._client("maarif-mufredat")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_federation.py -v`
Expected: FAIL — `ImportError: cannot import name 'config' from 'src.mcp_server'`.

- [ ] **Step 3: Create `src/mcp_server/config.py`**

```python
"""Runtime settings for ted-mcp, read once from the environment (.env via load_env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Canonical fleet endpoints and the env var that carries each key (spec §7).
SERVER_DEFAULTS: dict[str, tuple[str, str]] = {
    "maarif-mufredat": ("https://mufredat.cureonics.com/mcp", "MUFREDAT_MCP_API_KEY"),
    "egitim-kaynak": ("https://egitim-kaynak.cureonics.com/mcp", "EGITIM_KAYNAK_MCP_API_KEY"),
    "anamnesis": ("https://anamnesis-mcp.cureonics.workers.dev/mcp", "ANAMNESIS_MCP_API_KEY"),
}


@dataclass(frozen=True)
class ServerConfig:
    name: str
    url: str
    api_key: str


@dataclass(frozen=True)
class Settings:
    public_base_url: str
    allowed_hosts: tuple[str, ...]
    data_dir: Path
    oauth_db_path: Path
    dashboard_api_url: str
    dashboard_api_key: str
    servers: dict[str, ServerConfig] = field(default_factory=dict)


def load_settings(env: Mapping[str, str] | None = None, project_root: Path | None = None) -> Settings:
    env = os.environ if env is None else env
    root = PROJECT_ROOT if project_root is None else project_root
    base = (env.get("TED_MCP_PUBLIC_BASE_URL") or "https://mcp.tedy.online").strip().rstrip("/")
    hosts_raw = env.get("TED_MCP_ALLOWED_HOSTS") or base.split("://", 1)[-1].split("/", 1)[0]
    hosts = tuple(h.strip() for h in hosts_raw.split(",") if h.strip())
    data_dir = root / "output"
    servers = {
        name: ServerConfig(name=name, url=url, api_key=(env.get(key_env) or "").strip())
        for name, (url, key_env) in SERVER_DEFAULTS.items()
    }
    return Settings(
        public_base_url=base,
        allowed_hosts=hosts,
        data_dir=data_dir,
        oauth_db_path=data_dir / "ted_mcp_oauth.sqlite3",
        dashboard_api_url=(env.get("TED_DASHBOARD_API_URL") or "http://127.0.0.1:8085").rstrip("/"),
        dashboard_api_key=(env.get("TED_DASHBOARD_API_KEY") or "").strip(),
        servers=servers,
    )
```

- [ ] **Step 4: Create `src/mcp_server/coverage.py`**

```python
"""Coverage manifest: which fleet server answered, came back empty, degraded or was skipped.

Empty is not evidence of absence (fleet no-fabrication invariant); every retrieval tool
returns this manifest so the model can say what it did not see.
"""
from __future__ import annotations


class Coverage:
    def __init__(self) -> None:
        self._rows: dict[str, str] = {}

    def hit(self, server: str) -> None:
        self._rows[server] = "hit"

    def empty(self, server: str) -> None:
        self._rows[server] = "empty"

    def degraded(self, server: str, reason: str) -> None:
        self._rows[server] = f"degraded:{reason}"

    def skipped(self, server: str, reason: str) -> None:
        self._rows[server] = f"skipped:{reason}"

    def as_dict(self) -> dict[str, str]:
        return dict(self._rows)
```

- [ ] **Step 5: Create `src/mcp_server/federation.py`**

```python
"""Server-side calls to fleet MCP servers with an explicit expected result shape."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Literal

from src.mcp_client import McpClient
from src.mcp_server.config import Settings

logger = logging.getLogger(__name__)

MUFREDAT = "maarif-mufredat"
EGITIM_KAYNAK = "egitim-kaynak"
ANAMNESIS = "anamnesis"

_DECODER = json.JSONDecoder()


class FederationError(Exception):
    def __init__(self, server: str, tool: str, reason: str) -> None:
        super().__init__(f"{server}.{tool}: {reason}")
        self.server = server
        self.tool = tool
        self.reason = reason


def decode_json_stream(text: str) -> list[Any]:
    """Decode concatenated JSON values (FastMCP emits one text block per list item)."""
    values: list[Any] = []
    idx, end = 0, len(text)
    while True:
        while idx < end and text[idx].isspace():
            idx += 1
        if idx >= end:
            return values
        value, idx = _DECODER.raw_decode(text, idx)
        values.append(value)


class Federation:
    def __init__(self, settings: Settings, client_factory: Callable[..., Any] = McpClient) -> None:
        self._settings = settings
        self._factory = client_factory
        self._clients: dict[str, Any] = {}

    def configured(self, server: str) -> bool:
        cfg = self._settings.servers.get(server)
        return bool(cfg and cfg.api_key)

    def _client(self, server: str) -> Any:
        if server not in self._clients:
            cfg = self._settings.servers[server]
            self._clients[server] = self._factory(name=cfg.name, url=cfg.url, api_key=cfg.api_key)
        return self._clients[server]

    def call(self, server: str, tool: str, args: dict[str, Any], beklenen: Literal["liste", "nesne"]) -> Any:
        if not self.configured(server):
            raise FederationError(server, tool, "not_configured")
        result = self._client(server).call_tool(tool, args)
        if not result.ok:
            raise FederationError(server, tool, f"tool_error: {result.error}")
        try:
            values = decode_json_stream(result.text)
        except ValueError as exc:
            logger.warning("undecodable %s.%s response: %s", server, tool, exc)
            raise FederationError(server, tool, "undecodable_json") from exc
        if beklenen == "liste":
            if len(values) == 1 and isinstance(values[0], list):
                return values[0]
            return values
        if len(values) == 1 and isinstance(values[0], dict):
            return values[0]
        raise FederationError(server, tool, "unexpected_shape")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_federation.py -v`
Expected: 11 PASS.

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server/config.py src/mcp_server/coverage.py src/mcp_server/federation.py tests/test_mcp_federation.py
git commit -m "feat(ted-mcp): ayarlar, kapsam manifestosu ve beklenen-biçimli federasyon çağrısı

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 4: E-postaya bağlı OAuth deposu ve `tdyM_` anahtar CLI'si

**Files:**
- Create: `src/mcp_server/oauth_store.py`
- Create: `src/mcp_server/keys.py`
- Test: `tests/test_mcp_oauth_store.py`

**Interfaces:**
- Consumes: `src.roles.is_full(email) -> bool`; `config.load_settings()` (`oauth_db_path`).
- Produces:
  - Constants `CODE_TTL_SECONDS = 300`, `ACCESS_TTL_SECONDS = 3600`, `REFRESH_TTL_SECONDS = 2_592_000`, `STATIC_KEY_PREFIX = "tdyM_"`.
  - `oauth_store.TokenPair(access_token: str, refresh_token: str, expires_in: int, email: str)` (frozen dataclass).
  - `oauth_store.OAuthStore(path: Path, clock: Callable[[], float] = time.time)` with:
    - `issue_code(email, client_id, redirect_uri, code_challenge, code_challenge_method) -> str` (ValueError unless method is S256 and email is full)
    - `redeem_code(code, client_id, redirect_uri, code_verifier) -> TokenPair | None`
    - `refresh(refresh_token, client_id) -> TokenPair | None`
    - `principal(bearer: str) -> str | None`
    - `create_static_key(label: str, email: str) -> str`
    - `revoke_static_key(label: str) -> bool`
    - `list_static_keys() -> list[dict]`
  - `keys.main(argv: list[str] | None = None, store: OAuthStore | None = None) -> int` — subcommands `olustur --etiket L --email E`, `listele`, `iptal --etiket L`.

Kalıp kaynağı: `CureoHub/mcp-servers/egitim-kaynak-mcp/src/egitim_kaynak/oauth_store.py` (opak değer + SHA-256 hash, tek kullanımlık kod `UPDATE … WHERE used_at IS NULL`). Fark: `principal` e-postadır ve her istekte `roles.is_full` ile yeniden doğrulanır (liste değişirse eski token'lar anında düşer).

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_oauth_store.py`:

```python
"""OAuth store: single-use S256 codes, rotating refresh with reuse revocation, tdyM_ keys."""
import base64
import hashlib
import stat

import pytest

from src.mcp_server import keys, oauth_store
from src.mcp_server.oauth_store import OAuthStore

FULL = "drmahirkurt@gmail.com"
READER = "murzogluhulya@gmail.com"
CLIENT = "ted-mcp-public"
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
VERIFIER = "v" * 64


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store(tmp_path, clock):
    return OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)


def _pair(store):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    return store.redeem_code(code, CLIENT, REDIRECT, VERIFIER)


def test_code_round_trip_binds_email(store):
    pair = _pair(store)
    assert pair is not None
    assert pair.email == FULL
    assert pair.expires_in == oauth_store.ACCESS_TTL_SECONDS
    assert store.principal(pair.access_token) == FULL


def test_code_is_single_use(store):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is not None
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is None


@pytest.mark.parametrize("client,redirect,verifier", [
    ("other-client", REDIRECT, VERIFIER),
    (CLIENT, "https://grok.com/cb", VERIFIER),
    (CLIENT, REDIRECT, "w" * 64),
])
def test_code_redeem_rejects_mismatch(store, client, redirect, verifier):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, client, redirect, verifier) is None


def test_code_expires_after_five_minutes(store, clock):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    clock.now += oauth_store.CODE_TTL_SECONDS + 1
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is None


def test_issue_code_rejects_plain_pkce_and_non_full_email(store):
    with pytest.raises(ValueError):
        store.issue_code(FULL, CLIENT, REDIRECT, VERIFIER, "plain")
    with pytest.raises(ValueError):
        store.issue_code(READER, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")


def test_access_token_expires(store, clock):
    pair = _pair(store)
    clock.now += oauth_store.ACCESS_TTL_SECONDS + 1
    assert store.principal(pair.access_token) is None


def test_refresh_rotates_and_old_refresh_is_single_use(store):
    first = _pair(store)
    second = store.refresh(first.refresh_token, CLIENT)
    assert second is not None
    assert second.refresh_token != first.refresh_token
    assert store.principal(second.access_token) == FULL


def test_refresh_reuse_revokes_the_whole_family(store):
    first = _pair(store)
    second = store.refresh(first.refresh_token, CLIENT)
    assert store.refresh(first.refresh_token, CLIENT) is None  # replay
    assert store.principal(second.access_token) is None
    assert store.refresh(second.refresh_token, CLIENT) is None


def test_refresh_rejects_other_client_and_expiry(store, clock):
    first = _pair(store)
    assert store.refresh(first.refresh_token, "other-client") is None
    other = _pair(store)
    clock.now += oauth_store.REFRESH_TTL_SECONDS + 1
    assert store.refresh(other.refresh_token, CLIENT) is None


def test_roster_change_invalidates_existing_tokens(store, monkeypatch):
    pair = _pair(store)
    monkeypatch.setattr(oauth_store.roles, "is_full", lambda email: False)
    assert store.principal(pair.access_token) is None


def test_static_key_lifecycle(store):
    key = store.create_static_key("codex-mahir", FULL)
    assert key.startswith("tdyM_")
    assert store.principal(key) == FULL
    listed = store.list_static_keys()
    assert listed == [{"label": "codex-mahir", "email": FULL, "created_at": listed[0]["created_at"], "revoked": False}]
    assert store.revoke_static_key("codex-mahir") is True
    assert store.principal(key) is None
    assert store.revoke_static_key("codex-mahir") is False


def test_static_key_refused_for_reader_and_duplicate_label(store):
    with pytest.raises(ValueError):
        store.create_static_key("reader-key", READER)
    store.create_static_key("dup", FULL)
    with pytest.raises(ValueError):
        store.create_static_key("dup", FULL)


def test_dashboard_keys_and_garbage_are_not_principals(store):
    assert store.principal("tdyK_" + "a" * 40) is None
    assert store.principal("") is None
    assert store.principal("ünicode") is None


def test_database_file_is_private(tmp_path, clock):
    path = tmp_path / "oauth.sqlite3"
    OAuthStore(path, clock=clock)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_keys_cli_create_list_revoke(store, capsys):
    assert keys.main(["olustur", "--etiket", "grok", "--email", FULL], store=store) == 0
    created = capsys.readouterr().out.strip().splitlines()[-1]
    assert created.startswith("tdyM_")
    assert keys.main(["listele"], store=store) == 0
    assert "grok" in capsys.readouterr().out
    assert keys.main(["iptal", "--etiket", "grok"], store=store) == 0
    assert store.principal(created) is None
    assert keys.main(["olustur", "--etiket", "x", "--email", READER], store=store) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_oauth_store.py -v`
Expected: FAIL — `ImportError: cannot import name 'keys' from 'src.mcp_server'`.

- [ ] **Step 3: Create `src/mcp_server/oauth_store.py`**

```python
"""SQLite store for ted-mcp OAuth: codes, rotating refresh tokens and tdyM_ static keys.

Only SHA-256 hashes of issued values are stored. Every principal lookup re-checks the
household roster, so removing someone from src/roles.py invalidates their tokens at once.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src import roles

CODE_TTL_SECONDS = 300
ACCESS_TTL_SECONDS = 3600
REFRESH_TTL_SECONDS = 30 * 24 * 3600
STATIC_KEY_PREFIX = "tdyM_"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_code (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    challenge TEXT NOT NULL,
    challenge_method TEXT NOT NULL CHECK (challenge_method = 'S256'),
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);
CREATE TABLE IF NOT EXISTS oauth_access (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    family_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS oauth_refresh (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    family_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER,
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS static_key (
    value_hash TEXT PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);
"""


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    email: str


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OAuthStore:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self._path = Path(path)
        self._clock = clock
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self._path, 0o600)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> int:
        return int(self._clock())

    # -- authorization codes -------------------------------------------------------
    def issue_code(self, email: str, client_id: str, redirect_uri: str,
                   code_challenge: str, code_challenge_method: str) -> str:
        if (code_challenge_method or "").upper() != "S256" or not code_challenge:
            raise ValueError("only PKCE S256 is accepted")
        if not roles.is_full(email):
            raise ValueError("email is not a full-role roster member")
        code = secrets.token_urlsafe(32)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO oauth_code (value_hash, email, client_id, redirect_uri, challenge,"
                " challenge_method, expires_at) VALUES (?, ?, ?, ?, ?, 'S256', ?)",
                (_hash(code), email.strip().lower(), client_id, redirect_uri, code_challenge,
                 self._now() + CODE_TTL_SECONDS),
            )
        return code

    def redeem_code(self, code: str, client_id: str, redirect_uri: str,
                    code_verifier: str) -> TokenPair | None:
        if not (code and client_id and redirect_uri and code_verifier):
            return None
        try:
            challenge = _s256(code_verifier)
        except UnicodeEncodeError:
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT email FROM oauth_code WHERE value_hash = ? AND client_id = ? AND redirect_uri = ?"
                " AND challenge = ? AND expires_at > ? AND used_at IS NULL",
                (_hash(code), client_id, redirect_uri, challenge, now),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return None
            conn.execute("UPDATE oauth_code SET used_at = ? WHERE value_hash = ?", (now, _hash(code)))
            pair = self._issue_pair(conn, row["email"], client_id, secrets.token_hex(8), now)
            conn.execute("COMMIT")
        return pair

    # -- tokens --------------------------------------------------------------------
    def _issue_pair(self, conn: sqlite3.Connection, email: str, client_id: str,
                    family_id: str, now: int) -> TokenPair:
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO oauth_access (value_hash, email, family_id, expires_at) VALUES (?, ?, ?, ?)",
            (_hash(access), email, family_id, now + ACCESS_TTL_SECONDS),
        )
        conn.execute(
            "INSERT INTO oauth_refresh (value_hash, email, family_id, client_id, expires_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (_hash(refresh), email, family_id, client_id, now + REFRESH_TTL_SECONDS),
        )
        return TokenPair(access, refresh, ACCESS_TTL_SECONDS, email)

    def refresh(self, refresh_token: str, client_id: str) -> TokenPair | None:
        if not (refresh_token and client_id):
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT email, family_id, client_id, expires_at, used_at, revoked_at"
                " FROM oauth_refresh WHERE value_hash = ?",
                (_hash(refresh_token),),
            ).fetchone()
            if row is None or row["client_id"] != client_id or row["revoked_at"] is not None:
                conn.execute("ROLLBACK")
                return None
            if row["used_at"] is not None:
                # Replay of a rotated refresh token: treat the family as stolen.
                conn.execute("UPDATE oauth_access SET revoked_at = ? WHERE family_id = ?", (now, row["family_id"]))
                conn.execute("UPDATE oauth_refresh SET revoked_at = ? WHERE family_id = ?", (now, row["family_id"]))
                conn.execute("COMMIT")
                return None
            if row["expires_at"] <= now or not roles.is_full(row["email"]):
                conn.execute("ROLLBACK")
                return None
            conn.execute("UPDATE oauth_refresh SET used_at = ? WHERE value_hash = ?", (now, _hash(refresh_token)))
            pair = self._issue_pair(conn, row["email"], client_id, row["family_id"], now)
            conn.execute("COMMIT")
        return pair

    def principal(self, bearer: str) -> str | None:
        if not bearer or not bearer.isascii():
            return None
        digest = _hash(bearer)
        with self._connect() as conn:
            if bearer.startswith(STATIC_KEY_PREFIX):
                row = conn.execute(
                    "SELECT email FROM static_key WHERE value_hash = ? AND revoked_at IS NULL", (digest,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT email FROM oauth_access WHERE value_hash = ? AND expires_at > ? AND revoked_at IS NULL",
                    (digest, self._now()),
                ).fetchone()
        if row is None or not roles.is_full(row["email"]):
            return None
        return row["email"]

    # -- static keys ---------------------------------------------------------------
    def create_static_key(self, label: str, email: str) -> str:
        if not label or not roles.is_full(email):
            raise ValueError("static keys are issued only to full-role roster members")
        key = STATIC_KEY_PREFIX + secrets.token_urlsafe(32)
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO static_key (value_hash, label, email, created_at) VALUES (?, ?, ?, ?)",
                    (_hash(key), label, email.strip().lower(), self._now()),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"label already exists: {label}") from exc
        return key

    def revoke_static_key(self, label: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE static_key SET revoked_at = ? WHERE label = ? AND revoked_at IS NULL",
                (self._now(), label),
            )
        return cur.rowcount == 1

    def list_static_keys(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT label, email, created_at, revoked_at FROM static_key ORDER BY created_at, label"
            ).fetchall()
        return [
            {"label": r["label"], "email": r["email"], "created_at": r["created_at"], "revoked": r["revoked_at"] is not None}
            for r in rows
        ]
```

- [ ] **Step 4: Create `src/mcp_server/keys.py`**

```python
"""Manage tdyM_ static keys for MCP clients that cannot do OAuth.

    .venv/bin/python -m src.mcp_server.keys olustur --etiket codex-mahir --email drmahirkurt@gmail.com
    .venv/bin/python -m src.mcp_server.keys listele
    .venv/bin/python -m src.mcp_server.keys iptal --etiket codex-mahir

The key is printed once and never stored in clear text.
"""
from __future__ import annotations

import argparse
import sys

from src.mcp_server.oauth_store import OAuthStore


def _default_store() -> OAuthStore:
    from src.env_loader import load_env
    from src.mcp_server.config import load_settings

    load_env()
    return OAuthStore(load_settings().oauth_db_path)


def main(argv: list[str] | None = None, store: OAuthStore | None = None) -> int:
    parser = argparse.ArgumentParser(description="ted-mcp tdyM_ statik anahtarları")
    sub = parser.add_subparsers(dest="komut", required=True)
    create = sub.add_parser("olustur")
    create.add_argument("--etiket", required=True)
    create.add_argument("--email", required=True)
    sub.add_parser("listele")
    revoke = sub.add_parser("iptal")
    revoke.add_argument("--etiket", required=True)
    args = parser.parse_args(argv)
    store = store or _default_store()

    if args.komut == "olustur":
        try:
            key = store.create_static_key(args.etiket, args.email)
        except ValueError as exc:
            print(f"hata: {exc}", file=sys.stderr)
            return 2
        print("Anahtar yalnız bir kez gösterilir; güvenli bir yere kaydedin:")
        print(key)
        return 0
    if args.komut == "listele":
        for row in store.list_static_keys():
            state = "iptal" if row["revoked"] else "aktif"
            print(f"{row['label']}\t{row['email']}\t{row['created_at']}\t{state}")
        return 0
    if store.revoke_static_key(args.etiket):
        print(f"iptal edildi: {args.etiket}")
        return 0
    print(f"aktif anahtar bulunamadı: {args.etiket}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_oauth_store.py -v`
Expected: 17 PASS (parametrized mismatch test counts 3).

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server/oauth_store.py src/mcp_server/keys.py tests/test_mcp_oauth_store.py
git commit -m "feat(ted-mcp): e-postaya bağlı OAuth deposu (S256 kod, dönen yenileme) ve tdyM_ anahtar CLI'si

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 5: HTTP yüzeyi — metadata, istemci kaydı, CORS, host denetimi, Bearer kapısı, kimlikli MCP bağlantısı

**Files:**
- Create: `src/mcp_server/oauth_redirect.py`
- Create: `src/mcp_server/google_identity.py`
- Create: `src/mcp_server/http_app.py`
- Test: `tests/test_mcp_http_app.py`

**Interfaces:**
- Consumes: `config.Settings` (`public_base_url`, `allowed_hosts`), `oauth_store.OAuthStore.principal(bearer) -> str | None`, `roles.GOOGLE_CLIENT_ID`, `src.mcp_server.__version__`.
- Produces:
  - `oauth_redirect.ALLOWED_ORIGINS: tuple[str, ...]`, `is_allowed_redirect(uri: str) -> bool`, `is_allowed_cors_origin(origin: str) -> bool`.
  - `google_identity.IdentityError(Exception)` (`.reason: str`); `google_identity.verify_google_credential(credential: str, expected_nonce: str) -> str` (lower-case e-posta). Tip takma adı `IdentityVerifier = Callable[[str, str], str]`.
  - `http_app.CLIENT_ID = "ted-mcp-public"`, `http_app.REALM = "ted-mcp"`.
  - `http_app.build_app(settings: Settings, store: OAuthStore, mcp: FastMCP, verify_identity: IdentityVerifier = verify_google_credential, form_secret: bytes = b"", clock: Callable[[], float] = time.time) -> Starlette`.
  - Request identity contract: for every authorised `/mcp` request the gate writes `scope["state"]["ted_email"]`; tools read it as `ctx.request_context.request.state.ted_email` (mcp 1.28.1 puts the Starlette `Request` in `RequestContext.request`).

Tasarım notları:
- Ara katmanlar **saf ASGI** (BaseHTTPMiddleware değil): SSE akışlarını tamponlamaz ve `scope["state"]`'i taşıyıcıyla paylaşır. Sıra (en dıştan): `CorsMiddleware` → `HostGuardMiddleware` → `BearerGateMiddleware`.
- Taban URL istekten değil `settings.public_base_url`'den türetilir (Host başlığı sahtelenemesin).
- Bu görevde `/oauth/authorize` ve `/oauth/token` henüz yoktur; Görev 6 ekler.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_http_app.py`:

```python
"""HTTP surface: metadata, DCR, CORS, host guard, bearer gate and identity passthrough."""
import json

import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from src.mcp_server import google_identity, oauth_redirect
from src.mcp_server.config import load_settings
from src.mcp_server.http_app import build_app
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"


def _test_mcp() -> FastMCP:
    mcp = FastMCP(
        "test",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def kimim(ctx: Context) -> dict:
        return {"email": ctx.request_context.request.state.ted_email}

    return mcp


@pytest.fixture
def store(tmp_path):
    return OAuthStore(tmp_path / "oauth.sqlite3")


@pytest.fixture
def client(tmp_path, store):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    with TestClient(app, base_url=BASE) as c:
        yield c


def _rpc(method, params=None, id_=1):
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}


MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"])
def test_protected_resource_metadata(client, path):
    body = client.get(path).json()
    assert body["resource"] == f"{BASE}/mcp"
    assert body["authorization_servers"] == [BASE]
    assert body["bearer_methods_supported"] == ["header"]


def test_authorization_server_metadata_is_s256_only(client):
    body = client.get("/.well-known/oauth-authorization-server").json()
    assert body["issuer"] == BASE
    assert body["authorization_endpoint"] == f"{BASE}/oauth/authorize"
    assert body["token_endpoint"] == f"{BASE}/oauth/token"
    assert body["registration_endpoint"] == f"{BASE}/oauth/register"
    assert body["code_challenge_methods_supported"] == ["S256"]
    assert body["grant_types_supported"] == ["authorization_code", "refresh_token"]


def test_register_echoes_allowed_redirect_uris(client):
    r = client.post("/oauth/register", json={"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]})
    assert r.status_code == 201
    assert r.json()["client_id"] == "ted-mcp-public"
    assert r.json()["redirect_uris"] == ["https://claude.ai/api/mcp/auth_callback"]


def test_register_rejects_disallowed_redirect(client):
    r = client.post("/oauth/register", json={"redirect_uris": ["https://claude.ai.evil.com/cb"]})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_redirect_uri"


def test_mcp_without_bearer_is_401_with_resource_metadata(client):
    r = client.post("/mcp", json=_rpc("initialize"), headers={**MCP_HEADERS, "origin": "https://claude.ai"})
    assert r.status_code == 401
    challenge = r.headers["www-authenticate"]
    assert 'realm="ted-mcp"' in challenge
    assert f'resource_metadata="{BASE}/.well-known/oauth-protected-resource"' in challenge
    assert r.headers["access-control-allow-origin"] == "https://claude.ai"
    assert "www-authenticate" in r.headers["access-control-expose-headers"]


@pytest.mark.parametrize("bearer", ["tdyK_" + "a" * 40, "garbage", "ünicode"])
def test_unknown_bearers_are_401_not_500(client, bearer):
    r = client.post("/mcp", json=_rpc("initialize"), headers={**MCP_HEADERS, "authorization": f"Bearer {bearer}".encode("utf-8").decode("latin-1")})
    assert r.status_code == 401


def test_preflight_short_circuits_before_auth(client):
    ok = client.options("/mcp", headers={"origin": "https://grok.com", "access-control-request-method": "POST"})
    assert ok.status_code == 204
    assert ok.headers["access-control-allow-origin"] == "https://grok.com"
    bad = client.options("/mcp", headers={"origin": "https://evil.example", "access-control-request-method": "POST"})
    assert bad.status_code == 204
    assert "access-control-allow-origin" not in bad.headers


def test_host_guard_rejects_foreign_host(tmp_path, store):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    with TestClient(app, base_url="https://evil.example") as c:
        r = c.post("/mcp", json=_rpc("initialize"), headers=MCP_HEADERS)
    assert r.status_code == 400
    assert r.json()["error"] == "host_not_allowed"


def test_static_key_reaches_tool_with_identity(client, store):
    key = store.create_static_key("test", FULL)
    r = client.post(
        "/mcp",
        json=_rpc("tools/call", {"name": "kimim", "arguments": {}}),
        headers={**MCP_HEADERS, "authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    content = r.json()["result"]["content"][0]["text"]
    assert json.loads(content) == {"email": FULL}


def test_redirect_policy():
    assert oauth_redirect.is_allowed_redirect("https://chatgpt.com/connector_platform_oauth_redirect")
    assert oauth_redirect.is_allowed_redirect("https://oauth-redirect.googleusercontent.com/r/abc")
    assert oauth_redirect.is_allowed_redirect("http://127.0.0.1:53712/callback")
    assert oauth_redirect.is_allowed_redirect("http://localhost:33418/")
    assert not oauth_redirect.is_allowed_redirect("http://claude.ai/cb")
    assert not oauth_redirect.is_allowed_redirect("https://claude.ai.evil.com/cb")
    assert not oauth_redirect.is_allowed_redirect("https://claude.ai/cb#frag")
    assert not oauth_redirect.is_allowed_redirect("http://192.168.1.5:8080/cb")
    assert not oauth_redirect.is_allowed_redirect("not a url")


def test_google_identity_checks_nonce_and_verified_email(monkeypatch):
    def fake_verify(token, request, audience):
        assert audience == google_identity.roles.GOOGLE_CLIENT_ID
        return {"email": "DrMahirKurt@gmail.com", "email_verified": True, "nonce": token}

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", fake_verify)
    assert google_identity.verify_google_credential("n1", "n1") == FULL
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "other")
    assert exc.value.reason == "nonce_mismatch"

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token",
                        lambda t, r, a: {"email": FULL, "email_verified": False, "nonce": t})
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "n1")
    assert exc.value.reason == "email_not_verified"

    def raises(t, r, a):
        raise ValueError("bad signature")

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", raises)
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "n1")
    assert exc.value.reason == "invalid_token"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_http_app.py -v`
Expected: FAIL — `ImportError: cannot import name 'google_identity' from 'src.mcp_server'`.

- [ ] **Step 3: Create `src/mcp_server/oauth_redirect.py`**

```python
"""redirect_uri and CORS origin policy for the four web surfaces (fleet pattern).

Whole-origin match (scheme + netloc) against a fixed allowlist, so lookalikes such as
https://claude.ai.evil.com and scheme downgrades such as http://claude.ai are rejected.
Loopback is accepted on any port (RFC 8252): the code lands on the user's own machine.
"""
from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_ORIGINS = (
    "https://claude.ai",
    "https://claude.com",
    "https://chatgpt.com",
    "https://grok.com",
    "https://oauth-redirect.googleusercontent.com",
    "https://vscode.dev",
    "https://insiders.vscode.dev",
)
_LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")


def is_allowed_redirect(redirect_uri: str) -> bool:
    try:
        parsed = urlparse(redirect_uri)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.fragment:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.hostname in _LOOPBACK_HOSTS:
        return True
    return f"{parsed.scheme}://{parsed.netloc}" in ALLOWED_ORIGINS


def is_allowed_cors_origin(origin: str) -> bool:
    return origin in ALLOWED_ORIGINS
```

- [ ] **Step 4: Create `src/mcp_server/google_identity.py`**

```python
"""Verify a Google Identity Services credential for the OAuth consent step."""
from __future__ import annotations

from typing import Callable

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src import roles

IdentityVerifier = Callable[[str, str], str]


class IdentityError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def verify_google_credential(credential: str, expected_nonce: str) -> str:
    """Return the verified, lower-cased email or raise IdentityError."""
    try:
        info = id_token.verify_oauth2_token(credential, google_requests.Request(), roles.GOOGLE_CLIENT_ID)
    except ValueError as exc:
        raise IdentityError("invalid_token") from exc
    if not info.get("email_verified"):
        raise IdentityError("email_not_verified")
    if not expected_nonce or info.get("nonce") != expected_nonce:
        raise IdentityError("nonce_mismatch")
    return str(info.get("email", "")).strip().lower()
```

- [ ] **Step 5: Create `src/mcp_server/http_app.py`**

```python
"""Starlette app for ted-mcp: OAuth 2.1 discovery, DCR, CORS, host guard, bearer gate, MCP."""
from __future__ import annotations

import json
import time
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from src.mcp_server import __version__
from src.mcp_server.config import Settings
from src.mcp_server.google_identity import IdentityVerifier, verify_google_credential
from src.mcp_server.oauth_redirect import is_allowed_cors_origin, is_allowed_redirect
from src.mcp_server.oauth_store import OAuthStore

CLIENT_ID = "ted-mcp-public"
REALM = "ted-mcp"
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key == name:
            return value.decode("latin-1")
    return ""


async def _send_json(send: Send, status: int, body: dict[str, Any], extra: list[tuple[bytes, bytes]] | None = None) -> None:
    payload = json.dumps(body).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers + (extra or [])})
    await send({"type": "http.response.body", "body": payload})


class CorsMiddleware:
    """Outermost: answers preflight before auth and exposes WWW-Authenticate to browsers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        origin = _header(scope, b"origin")
        allowed = bool(origin) and is_allowed_cors_origin(origin)
        cors = [
            (b"access-control-allow-origin", origin.encode("latin-1")),
            (b"access-control-expose-headers", b"mcp-session-id, www-authenticate"),
            (b"vary", b"Origin"),
        ] if allowed else []
        if scope["method"] == "OPTIONS" and _header(scope, b"access-control-request-method"):
            headers = cors + ([
                (b"access-control-allow-methods", b"GET, POST, DELETE, OPTIONS"),
                (b"access-control-allow-headers", b"authorization, content-type, mcp-session-id, mcp-protocol-version"),
                (b"access-control-max-age", b"600"),
            ] if allowed else [])
            await send({"type": "http.response.start", "status": 204, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_with_cors(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start" and cors:
                message = {**message, "headers": list(message.get("headers") or []) + cors}
            await send(message)

        await self.app(scope, receive, send_with_cors)


class HostGuardMiddleware:
    """DNS-rebinding guard for /mcp: only the public host(s) and loopback."""

    def __init__(self, app: ASGIApp, allowed_hosts: tuple[str, ...]) -> None:
        self.app = app
        self.allowed = set(allowed_hosts) | _LOOPBACK_HOSTS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            host = _header(scope, b"host").rsplit(":", 1)[0].strip("[]").lower()
            if host not in self.allowed:
                await _send_json(send, 400, {"error": "host_not_allowed"})
                return
        await self.app(scope, receive, send)


class BearerGateMiddleware:
    """Resolves the bearer to a roster email and hands it to tools via scope['state']."""

    def __init__(self, app: ASGIApp, store: OAuthStore, base_url: str) -> None:
        self.app = app
        self.store = store
        self.challenge = f'Bearer realm="{REALM}", resource_metadata="{base_url}/.well-known/oauth-protected-resource"'

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            auth = _header(scope, b"authorization")
            token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
            email = self.store.principal(token) if token else None
            if email is None:
                await _send_json(send, 401, {"error": "unauthorized"},
                                 [(b"www-authenticate", self.challenge.encode("latin-1"))])
                return
            scope.setdefault("state", {})["ted_email"] = email
        await self.app(scope, receive, send)


def build_app(
    settings: Settings,
    store: OAuthStore,
    mcp: FastMCP,
    verify_identity: IdentityVerifier = verify_google_credential,
    form_secret: bytes = b"",
    clock: Callable[[], float] = time.time,
) -> Starlette:
    # verify_identity, form_secret and clock are used by the consent/token routes (Task 6).
    base = settings.public_base_url

    async def health(request: Request) -> Response:
        return JSONResponse({"status": "ok", "version": __version__})

    async def protected_resource(request: Request) -> Response:
        return JSONResponse({
            "resource": f"{base}/mcp",
            "authorization_servers": [base],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["edupedia"],
        })

    async def authorization_server(request: Request) -> Response:
        return JSONResponse({
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["edupedia"],
        })

    async def register(request: Request) -> Response:
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"error": "invalid_client_metadata"}, status_code=400)
        uris = body.get("redirect_uris") if isinstance(body, dict) else None
        if not isinstance(uris, list) or not uris or not all(isinstance(u, str) and is_allowed_redirect(u) for u in uris):
            return JSONResponse({"error": "invalid_redirect_uri"}, status_code=400)
        return JSONResponse({
            "client_id": CLIENT_ID,
            "redirect_uris": uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }, status_code=201)

    streamable = mcp.streamable_http_app()
    routes = [
        Route("/health", health),
        Route("/.well-known/oauth-protected-resource", protected_resource),
        Route("/.well-known/oauth-protected-resource/mcp", protected_resource),
        Route("/.well-known/oauth-authorization-server", authorization_server),
        Route("/oauth/register", register, methods=["POST"]),
        Mount("/", app=streamable),
    ]
    # Middleware order: first entry is outermost. Pure ASGI classes keep SSE unbuffered and
    # share scope["state"] with the streamable transport's Request (identity contract).
    return Starlette(
        routes=routes,
        lifespan=streamable.router.lifespan_context,
        middleware=[
            Middleware(CorsMiddleware),
            Middleware(HostGuardMiddleware, allowed_hosts=settings.allowed_hosts),
            Middleware(BearerGateMiddleware, store=store, base_url=base),
        ],
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_http_app.py -v`
Expected: 17 PASS (parametrized cases included).

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server/oauth_redirect.py src/mcp_server/google_identity.py src/mcp_server/http_app.py tests/test_mcp_http_app.py
git commit -m "feat(ted-mcp): OAuth keşfi, DCR, CORS, host denetimi ve kimliği araca taşıyan Bearer kapısı

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 6: Google girişli onay sayfası, token ucu ve uçtan uca OAuth akışı

**Files:**
- Modify: `src/mcp_server/http_app.py` (imports, form-state helpers, consent page, `/oauth/authorize` GET+POST, `/oauth/token`, `form_secret` check)
- Test: `tests/test_mcp_oauth_flow.py`

**Interfaces:**
- Consumes: Task 5 `build_app(settings, store, mcp, verify_identity, form_secret, clock)`, `CLIENT_ID`, `is_allowed_redirect`; Task 4 `OAuthStore.issue_code/redeem_code/refresh`, `TokenPair`; `google_identity.IdentityError`; `roles.is_full`.
- Produces:
  - `http_app.FORM_TTL_SECONDS = 600`.
  - `http_app.sign_form_state(params: dict[str, str], secret: bytes, now: float) -> str` and `http_app.read_form_state(token: str, secret: bytes, now: float) -> dict[str, str]` (raises `ValueError("form_state_invalid" | "form_state_expired")`).
  - `http_app.nonce_for(form_state: str) -> str` = `hashlib.sha256(form_state.encode()).hexdigest()`.
  - Routes: `GET/POST /oauth/authorize`, `POST /oauth/token`. `build_app` raises `ValueError` when `form_secret` is shorter than 32 bytes.

Akış: GET, OAuth parametrelerini doğrular ve imzalı, 10 dk geçerli bir `form_state` üretir. Sayfa Google Identity Services düğmesini `nonce = sha256(form_state)` ile başlatır. POST, parametreleri **yalnız** imzalı `form_state`'ten okur (gizli alanlar sahtelenemez), Google kimliğini doğrular, `full` rol değilse 403 döner, aksi hâlde tek kullanımlık kod üretip `redirect_uri`'ye yönlendirir.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_oauth_flow.py`:

```python
"""End-to-end OAuth: consent page → Google identity → code → tokens → MCP tool with identity."""
import base64
import hashlib
import json
import re
from urllib.parse import parse_qs, urlparse

import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from src.mcp_server import http_app
from src.mcp_server.config import load_settings
from src.mcp_server.google_identity import IdentityError
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
READER = "murzogluhulya@gmail.com"
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
VERIFIER = "v" * 64
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def _challenge(v: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()


def _test_mcp() -> FastMCP:
    mcp = FastMCP("test", stateless_http=True, json_response=True,
                  transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

    @mcp.tool()
    def kimim(ctx: Context) -> dict:
        return {"email": ctx.request_context.request.state.ted_email}

    return mcp


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now


class Verifier:
    """Test double: the 'credential' is the email; asserts the nonce binds to form_state."""

    def __init__(self):
        self.expected_nonce = None
        self.error = None

    def __call__(self, credential, nonce):
        assert nonce == self.expected_nonce
        if self.error:
            raise IdentityError(self.error)
        return credential


@pytest.fixture
def ctx(tmp_path):
    clock, verifier = Clock(), Verifier()
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = http_app.build_app(settings, store, _test_mcp(), verify_identity=verifier,
                             form_secret=b"s" * 32, clock=clock)
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        yield client, verifier, clock, store


def _authorize_params(**over):
    params = {"response_type": "code", "client_id": http_app.CLIENT_ID, "redirect_uri": REDIRECT,
              "state": "st-123", "code_challenge": _challenge(VERIFIER), "code_challenge_method": "S256"}
    params.update(over)
    return params


def _start(client, verifier, **over):
    r = client.get("/oauth/authorize", params=_authorize_params(**over))
    assert r.status_code == 200
    form_state = re.search(r'name="form_state" value="([^"]+)"', r.text).group(1)
    verifier.expected_nonce = http_app.nonce_for(form_state)
    return form_state


def test_consent_page_embeds_google_signin_and_nonce(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    page = client.get("/oauth/authorize", params=_authorize_params()).text
    assert "accounts.google.com/gsi/client" in page
    assert http_app.roles.GOOGLE_CLIENT_ID in page
    assert "claude.ai" in page
    assert form_state


@pytest.mark.parametrize("over,reason", [
    ({"redirect_uri": "https://claude.ai.evil.com/cb"}, "redirect_uri"),
    ({"code_challenge_method": "plain"}, "S256"),
    ({"code_challenge": ""}, "code_challenge"),
    ({"response_type": "token"}, "response_type"),
    ({"client_id": "someone-else"}, "client_id"),
])
def test_authorize_get_rejects_bad_requests(ctx, over, reason):
    client, _, _, _ = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(**over))
    assert r.status_code == 400
    assert reason in r.text


def test_full_round_trip_to_mcp_and_refresh(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": FULL})
    assert r.status_code == 302
    loc = urlparse(r.headers["location"])
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == REDIRECT
    query = parse_qs(loc.query)
    assert query["state"] == ["st-123"]

    tok = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": query["code"][0], "redirect_uri": REDIRECT,
        "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER})
    assert tok.status_code == 200
    assert tok.headers["cache-control"] == "no-store"
    body = tok.json()
    assert body["token_type"] == "Bearer" and body["expires_in"] == 3600 and body["refresh_token"]

    call = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                     "params": {"name": "kimim", "arguments": {}}},
                       headers={**MCP_HEADERS, "authorization": f"Bearer {body['access_token']}"})
    assert call.status_code == 200
    assert json.loads(call.json()["result"]["content"][0]["text"]) == {"email": FULL}

    again = client.post("/oauth/token", data={"grant_type": "refresh_token", "refresh_token": body["refresh_token"],
                                              "client_id": http_app.CLIENT_ID})
    assert again.status_code == 200
    assert again.json()["access_token"] != body["access_token"]


def test_reader_role_is_refused_without_code(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": READER})
    assert r.status_code == 403
    assert "location" not in r.headers


def test_identity_failure_is_401(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    verifier.error = "nonce_mismatch"
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": FULL})
    assert r.status_code == 401


def test_tampered_and_expired_form_state(ctx):
    client, verifier, clock, _ = ctx
    form_state = _start(client, verifier)
    payload, sig = form_state.split(".")
    tampered = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB") + "." + sig
    assert client.post("/oauth/authorize", data={"form_state": tampered, "credential": FULL}).status_code == 400
    clock.now += http_app.FORM_TTL_SECONDS + 1
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": FULL})
    assert r.status_code == 400
    assert "form_state_expired" in r.text


def test_token_endpoint_errors(ctx):
    client, _, _, _ = ctx
    bad = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": "nope", "redirect_uri": REDIRECT,
                                            "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER})
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_grant"
    evil = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": "x",
                                             "redirect_uri": "https://evil.example/cb",
                                             "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER})
    assert evil.status_code == 400 and evil.json()["error"] == "invalid_grant"
    other = client.post("/oauth/token", data={"grant_type": "client_credentials"})
    assert other.status_code == 400 and other.json()["error"] == "unsupported_grant_type"


def test_state_is_escaped_on_the_consent_page(ctx):
    client, _, _, _ = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(state='"><script>alert(1)</script>'))
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text


def test_form_state_helpers_round_trip():
    token = http_app.sign_form_state({"a": "1"}, b"k" * 32, now=100.0)
    assert http_app.read_form_state(token, b"k" * 32, now=100.0 + 10) == {"a": "1"}
    with pytest.raises(ValueError, match="form_state_invalid"):
        http_app.read_form_state(token, b"x" * 32, now=110.0)
    with pytest.raises(ValueError, match="form_state_invalid"):
        http_app.read_form_state(token.split(".")[0] + ".ü" + "0" * 63, b"k" * 32, now=110.0)
    with pytest.raises(ValueError, match="form_state_expired"):
        http_app.read_form_state(token, b"k" * 32, now=100.0 + http_app.FORM_TTL_SECONDS + 1)


def test_build_app_requires_form_secret(tmp_path):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    with pytest.raises(ValueError):
        http_app.build_app(settings, OAuthStore(tmp_path / "o.sqlite3"), _test_mcp(), form_secret=b"short")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_oauth_flow.py -v`
Expected: FAIL — `AttributeError: module 'src.mcp_server.http_app' has no attribute 'nonce_for'`.

- [ ] **Step 3: Add imports and form-state helpers to `src/mcp_server/http_app.py`**

Replace the import block header lines

```python
import json
import time
from typing import Any, Callable
```

with

```python
import base64
import hashlib
import hmac
import html
import json
import time
from typing import Any, Callable
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
```

and add, after the `from src.mcp_server.oauth_store import OAuthStore` line:

```python
from src import roles
from src.mcp_server.google_identity import IdentityError
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse
```

Add below `_LOOPBACK_HOSTS = {...}`:

```python
FORM_TTL_SECONDS = 600
_FORM_KEYS = ("client_id", "redirect_uri", "state", "code_challenge", "code_challenge_method", "scope", "resource")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_form_state(params: dict[str, str], secret: bytes, now: float) -> str:
    payload = _b64u(json.dumps({"p": params, "exp": int(now) + FORM_TTL_SECONDS}, sort_keys=True).encode())
    sig = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_form_state(token: str, secret: bytes, now: float) -> dict[str, str]:
    try:
        payload, sig = token.split(".", 1)
        expected = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig.encode("utf-8"), expected.encode("ascii")):
            raise ValueError("form_state_invalid")
        data = json.loads(_b64u_decode(payload))
    except (ValueError, UnicodeEncodeError) as exc:
        if str(exc) == "form_state_invalid":
            raise
        raise ValueError("form_state_invalid") from exc
    if int(data.get("exp", 0)) < int(now):
        raise ValueError("form_state_expired")
    return {k: str(v) for k, v in (data.get("p") or {}).items()}


def nonce_for(form_state: str) -> str:
    return hashlib.sha256(form_state.encode("ascii")).hexdigest()


def _with_query(uri: str, extra: dict[str, str]) -> str:
    parts = urlparse(uri)
    query = parse_qsl(parts.query, keep_blank_values=True) + list(extra.items())
    return urlunparse(parts._replace(query=urlencode(query)))


_CONSENT_PAGE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TEDY edupedia bağlantısı</title>
<style>
body{{font-family:"IBM Plex Sans",system-ui,sans-serif;background:#f4f4f4;color:#161616;margin:0;padding:48px 16px}}
main{{max-width:480px;margin:auto;background:#fff;padding:32px;border-top:4px solid #0f62fe}}
h1{{font-size:1.5rem;font-weight:400;margin:0 0 16px}} p{{line-height:1.5}} code{{background:#e0e0e0;padding:2px 4px}}
</style>
<script src="https://accounts.google.com/gsi/client" async></script></head>
<body><main>
<h1>edupedia'yı TEDY hesabına bağla</h1>
<p><code>{origin}</code> uygulaması, Google hesabınızla TEDY edupedia araçlarını kullanmak için izin istiyor.
Yalnız TEDY aile listesindeki tam yetkili hesaplar onay verebilir.</p>
<form id="consent" method="post" action="/oauth/authorize">
<input type="hidden" name="form_state" value="{form_state}">
<input type="hidden" name="credential" id="credential" value="">
</form>
<div id="g_id_onload" data-client_id="{client_id}" data-nonce="{nonce}" data-callback="tedyConsent"
     data-auto_prompt="false"></div>
<div class="g_id_signin" data-type="standard" data-text="continue_with" data-locale="tr"></div>
<script>function tedyConsent(r){{document.getElementById("credential").value=r.credential;document.getElementById("consent").submit();}}</script>
</main></body></html>"""
```

- [ ] **Step 4: Add the consent and token routes inside `build_app`**

At the top of `build_app` (after `base = settings.public_base_url`) add:

```python
    if len(form_secret) < 32:
        raise ValueError("form_secret must be at least 32 bytes")
```

Add these handlers after `register` and before `streamable = mcp.streamable_http_app()`:

```python
    def _bad(reason: str) -> Response:
        return PlainTextResponse(f"Geçersiz yetkilendirme isteği: {reason}", status_code=400)

    async def authorize(request: Request) -> Response:
        if request.method == "GET":
            q = request.query_params
            if q.get("response_type") != "code":
                return _bad("response_type")
            if q.get("client_id") != CLIENT_ID:
                return _bad("client_id")
            redirect_uri = q.get("redirect_uri", "")
            if not is_allowed_redirect(redirect_uri):
                return _bad("redirect_uri")
            if not q.get("code_challenge"):
                return _bad("code_challenge")
            if (q.get("code_challenge_method") or "").upper() != "S256":
                return _bad("code_challenge_method must be S256")
            params = {k: q.get(k, "") for k in _FORM_KEYS}
            form_state = sign_form_state(params, form_secret, clock())
            parsed = urlparse(redirect_uri)
            page = _CONSENT_PAGE.format(
                origin=html.escape(f"{parsed.scheme}://{parsed.netloc}"),
                form_state=html.escape(form_state),
                client_id=html.escape(roles.GOOGLE_CLIENT_ID),
                nonce=html.escape(nonce_for(form_state)),
            )
            return HTMLResponse(page, headers={"cache-control": "no-store", "x-frame-options": "DENY"})

        form = await request.form()
        form_state = str(form.get("form_state", ""))
        try:
            params = read_form_state(form_state, form_secret, clock())
        except ValueError as exc:
            return PlainTextResponse(str(exc), status_code=400)
        try:
            email = verify_identity(str(form.get("credential", "")), nonce_for(form_state))
        except IdentityError as exc:
            return PlainTextResponse(f"Google kimliği doğrulanamadı: {exc.reason}", status_code=401)
        if not roles.is_full(email):
            return PlainTextResponse("Bu hesap TEDY edupedia bağlantısını onaylayamaz.", status_code=403)
        code = store.issue_code(email, params["client_id"], params["redirect_uri"],
                                params["code_challenge"], params["code_challenge_method"])
        extra = {"code": code}
        if params.get("state"):
            extra["state"] = params["state"]
        return RedirectResponse(_with_query(params["redirect_uri"], extra), status_code=302)

    def _token_response(pair: Any) -> Response:
        return JSONResponse(
            {"access_token": pair.access_token, "token_type": "Bearer", "expires_in": pair.expires_in,
             "refresh_token": pair.refresh_token, "scope": "edupedia"},
            headers={"cache-control": "no-store", "pragma": "no-cache"},
        )

    def _grant_error(error: str) -> Response:
        return JSONResponse({"error": error}, status_code=400, headers={"cache-control": "no-store"})

    async def token(request: Request) -> Response:
        form = await request.form()
        grant = form.get("grant_type")
        client_id = str(form.get("client_id", ""))
        if grant == "authorization_code":
            redirect_uri = str(form.get("redirect_uri", ""))
            if client_id != CLIENT_ID or not is_allowed_redirect(redirect_uri):
                return _grant_error("invalid_grant")
            pair = store.redeem_code(str(form.get("code", "")), client_id, redirect_uri,
                                     str(form.get("code_verifier", "")))
            return _token_response(pair) if pair else _grant_error("invalid_grant")
        if grant == "refresh_token":
            if client_id != CLIENT_ID:
                return _grant_error("invalid_grant")
            pair = store.refresh(str(form.get("refresh_token", "")), client_id)
            return _token_response(pair) if pair else _grant_error("invalid_grant")
        return _grant_error("unsupported_grant_type")
```

Add to `routes`, right after the `/oauth/register` route:

```python
        Route("/oauth/authorize", authorize, methods=["GET", "POST"]),
        Route("/oauth/token", token, methods=["POST"]),
```

Remove the now-stale comment line `# verify_identity, form_secret and clock are used by the consent/token routes (Task 6).`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_oauth_flow.py tests/test_mcp_http_app.py -v`
Expected: all PASS (oauth flow 16 incl. parametrized + Task 5's 17).

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server/http_app.py tests/test_mcp_oauth_flow.py
git commit -m "feat(ted-mcp): Google girişli onay sayfası, imzalı form_state, token ve yenileme uçları

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 7: FastMCP sunucusu, `Tools` sınıfı, `edupedia_durum` ve süreç girişi

**Files:**
- Create: `src/mcp_server/tools.py`
- Create: `src/mcp_server/server.py`
- Modify: `src/mcp_server/http_app.py` (append `create_app_from_env` and `main`)
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `config.Settings`, `federation.Federation.call/configured`, `federation.FederationError`, `coverage.Coverage`, `gates.gate_count()`, `vendor_sync.load_provenance()`, `roles.role_of()`, `http_app.build_app(...)`, `oauth_store.OAuthStore`.
- Produces:
  - `tools.PROJECT_ROOT: Path`; `tools.app_revision(root: Path = PROJECT_ROOT) -> str | None` (reads `REVISION`, `None` when absent/blank).
  - `tools.Tools(settings: Settings, federation: Federation, clock: Callable[[], float] = time.time)` with `durum(email: str, canli: bool = False) -> dict`. Later tasks add `rehber`, `baglam`, `kapsam`, `kaynak_oku` to this class.
  - `server.caller_email(ctx: Context) -> str` (raises `ToolError("yetkisiz: …")` when no roster identity).
  - `server.build_server(tools: Tools) -> FastMCP` registering `edupedia_durum(ctx, canli: bool = False)`; `serverInfo.version == src.mcp_server.__version__`.
  - `http_app.create_app_from_env(env: Mapping[str, str] | None = None) -> Starlette` (requires `TED_MCP_FORM_SECRET` ≥ 32 bytes); `http_app.main() -> None` (uvicorn on `TED_MCP_HOST` default `127.0.0.1`, `TED_MCP_PORT` default `8087`).

`edupedia_durum` yanıt şeması (Türkçe alanlar): `status: "ok"`, `surum`, `app_revision`, `kullanici: {email, rol}`, `kapi_sayisi: 16`, `vendor: {kaynak_commit, esitlendi}`, `filo: {sunucu: "yapılandırılmış" | "anahtar yok"}`, `dashboard_anahtari: bool`, `medya_butcesi: null`, `notlar: [...]`, `mcp_verified: false`, ve `canli=True` ise `coverage` (her yapılandırılmış sunucu için hafif bir sağlık çağrısı).

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_server.py`:

```python
"""FastMCP server wiring: identity-aware edupedia_durum, version single source, env entry."""
import json

import pytest
from starlette.testclient import TestClient

from src.mcp_server import __version__, http_app, server, tools
from src.mcp_server.config import load_settings
from src.mcp_server.federation import Federation, FederationError
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


class FakeFederation:
    def __init__(self, configured=("maarif-mufredat",), fail=()):
        self._configured = set(configured)
        self._fail = set(fail)
        self.calls = []

    def configured(self, server):
        return server in self._configured

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool))
        if server in self._fail:
            raise FederationError(server, tool, "timeout")
        return {"status": "ok"}


def _settings(tmp_path, **env):
    base = {"TED_MCP_PUBLIC_BASE_URL": BASE, "MUFREDAT_MCP_API_KEY": "k"}
    base.update(env)
    return load_settings(base, project_root=tmp_path)


def _sse_json(response):
    for line in response.text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return response.json()


def test_app_revision_reads_revision_file(tmp_path):
    assert tools.app_revision(tmp_path) is None
    (tmp_path / "REVISION").write_text("  \n", encoding="utf-8")
    assert tools.app_revision(tmp_path) is None
    (tmp_path / "REVISION").write_text("abc1234\n", encoding="utf-8")
    assert tools.app_revision(tmp_path) == "abc1234"


def test_durum_reports_identity_fleet_and_gates(tmp_path):
    t = tools.Tools(_settings(tmp_path, TED_DASHBOARD_API_KEY="tdyK_x"), FakeFederation())
    body = t.durum(FULL)
    assert body["status"] == "ok"
    assert body["surum"] == __version__
    assert body["kullanici"] == {"email": FULL, "rol": "full"}
    assert body["kapi_sayisi"] == 16
    assert body["filo"]["maarif-mufredat"] == "yapılandırılmış"
    assert body["filo"]["anamnesis"] == "anahtar yok"
    assert body["dashboard_anahtari"] is True
    assert body["medya_butcesi"] is None
    assert body["mcp_verified"] is False
    assert body["vendor"]["kaynak_commit"]
    assert "coverage" not in body


def test_durum_live_probe_builds_coverage(tmp_path):
    fed = FakeFederation(configured=("maarif-mufredat", "egitim-kaynak"), fail=("egitim-kaynak",))
    body = tools.Tools(_settings(tmp_path), fed).durum(FULL, canli=True)
    assert body["coverage"]["maarif-mufredat"] == "hit"
    assert body["coverage"]["egitim-kaynak"] == "degraded:timeout"
    assert body["coverage"]["anamnesis"] == "skipped:anahtar yok"


def _client(tmp_path, store):
    settings = _settings(tmp_path)
    mcp = server.build_server(tools.Tools(settings, FakeFederation()))
    app = http_app.build_app(settings, store, mcp, form_secret=b"s" * 32)
    return TestClient(app, base_url=BASE)


def test_initialize_reports_app_version_and_tool_list(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    auth = {**MCP_HEADERS, "authorization": f"Bearer {key}"}
    with _client(tmp_path, store) as c:
        init = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}, headers=auth))
        assert init["result"]["serverInfo"]["version"] == __version__
        listed = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=auth))
        names = {t["name"] for t in listed["result"]["tools"]}
        assert "edupedia_durum" in names
        durum = next(t for t in listed["result"]["tools"] if t["name"] == "edupedia_durum")
        assert durum["annotations"]["readOnlyHint"] is True


def test_tool_call_carries_caller_identity(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    with _client(tmp_path, store) as c:
        r = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                           "params": {"name": "edupedia_durum", "arguments": {}}},
                             headers={**MCP_HEADERS, "authorization": f"Bearer {key}"}))
    body = json.loads(r["result"]["content"][0]["text"])
    assert body["kullanici"]["email"] == FULL


def test_create_app_from_env_requires_form_secret(tmp_path):
    with pytest.raises(ValueError):
        http_app.create_app_from_env({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path)})
    app = http_app.create_app_from_env({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path),
                                        "TED_MCP_FORM_SECRET": "f" * 40})
    assert app is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_server.py -v`
Expected: FAIL — `ImportError: cannot import name 'server' from 'src.mcp_server'`.

- [ ] **Step 3: Create `src/mcp_server/tools.py`**

```python
"""Business logic for ted-mcp tools, kept free of FastMCP so it is unit-testable."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from src import roles
from src.mcp_server import __version__, gates, vendor_sync
from src.mcp_server.config import Settings
from src.mcp_server.coverage import Coverage
from src.mcp_server.federation import ANAMNESIS, EGITIM_KAYNAK, MUFREDAT, Federation, FederationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Lightweight health call per fleet server for edupedia_durum(canli=True).
_HEALTH_CALLS: dict[str, tuple[str, dict[str, Any]]] = {
    MUFREDAT: ("server_info", {}),
    EGITIM_KAYNAK: ("kb_server_info", {}),
    ANAMNESIS: ("corpus_stats", {"collection": "edupedia:run:000000000000"}),
}


def app_revision(root: Path = PROJECT_ROOT) -> str | None:
    """Deploy revision from a REVISION file next to the project root; None when absent."""
    try:
        text = (root / "REVISION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


class Tools:
    def __init__(self, settings: Settings, federation: Federation, clock: Callable[[], float] = time.time) -> None:
        self.settings = settings
        self.federation = federation
        self.clock = clock

    def durum(self, email: str, canli: bool = False) -> dict[str, Any]:
        provenance = vendor_sync.load_provenance()
        filo = {
            name: ("yapılandırılmış" if self.federation.configured(name) else "anahtar yok")
            for name in self.settings.servers
        }
        body: dict[str, Any] = {
            "status": "ok",
            "surum": __version__,
            "app_revision": app_revision(),
            "kullanici": {"email": email, "rol": roles.role_of(email)},
            "kapi_sayisi": gates.gate_count(),
            "vendor": {"kaynak_commit": provenance.get("source_commit"), "esitlendi": provenance.get("synced_at")},
            "filo": filo,
            "dashboard_anahtari": bool(self.settings.dashboard_api_key),
            "medya_butcesi": None,
            "notlar": [
                "Medya bütçesi, derleme ve yayın araçları sonraki alt projede gelir.",
                "Boş sonuç yokluk kanıtı değildir; her getirim aracı kapsam manifestosu döner.",
            ],
            "mcp_verified": False,
        }
        if canli:
            cov = Coverage()
            for name in self.settings.servers:
                if not self.federation.configured(name):
                    cov.skipped(name, "anahtar yok")
                    continue
                tool, args = _HEALTH_CALLS[name]
                try:
                    self.federation.call(name, tool, args, beklenen="nesne")
                    cov.hit(name)
                except FederationError as exc:
                    cov.degraded(name, exc.reason)
            body["coverage"] = cov.as_dict()
        return body
```

- [ ] **Step 4: Create `src/mcp_server/server.py`**

```python
"""FastMCP registration for ted-mcp. Tool bodies live in tools.Tools."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from src import roles
from src.mcp_server import __version__
from src.mcp_server.tools import Tools

_RO = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

INSTRUCTIONS = (
    "TEDY edupedia orkestratörü. Türkiye Yüzyılı Maarif Modeli'ne hizalı etkileşimli öğrenim modülleri "
    "için müfredat doğrulama, ders kitabı çerçevesi ve açık eğitsel kaynakları sunar. Her zaman "
    "edupedia_rehber('akis') ile başla ve araç sırasını izle. Boş sonuç yokluk kanıtı değildir; "
    "coverage manifestosunu kullanıcıya bildir. Tüm çıktılar mcp_verified=false."
)


def caller_email(ctx: Context) -> str:
    """Roster email set by the bearer gate; tools refuse to run without it."""
    request = getattr(ctx.request_context, "request", None)
    state = getattr(request, "state", None)
    email = getattr(state, "ted_email", None) if state is not None else None
    if not email or not roles.is_full(email):
        raise ToolError("yetkisiz: bu araç yalnız TEDY aile listesindeki tam yetkili hesaplarla çalışır")
    return email


def build_server(tools: Tools) -> FastMCP:
    mcp = FastMCP(
        "TEDY edupedia",
        instructions=INSTRUCTIONS,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    # FastMCP drops `version`; without this serverInfo.version reports the SDK version.
    mcp._mcp_server.version = __version__

    @mcp.tool(annotations=_RO)
    def edupedia_durum(ctx: Context, canli: bool = False) -> dict[str, Any]:
        """Sunucu sürümü, kullanıcı, kapı sayısı ve filo yapılandırması. canli=true filo sağlığını yoklar."""
        return tools.durum(caller_email(ctx), canli=canli)

    return mcp
```

- [ ] **Step 5: Append the process entry to `src/mcp_server/http_app.py`**

Add `from typing import Mapping` to the typing import line (`from typing import Any, Callable, Mapping`) and append at the end of the file:

```python
def create_app_from_env(env: Mapping[str, str] | None = None) -> Starlette:
    """Wire settings, store, federation, tools and server from the environment."""
    import os
    from pathlib import Path

    from src.mcp_server.config import load_settings
    from src.mcp_server.federation import Federation
    from src.mcp_server.server import build_server
    from src.mcp_server.tools import Tools

    env = os.environ if env is None else env
    secret = (env.get("TED_MCP_FORM_SECRET") or "").encode("utf-8")
    if len(secret) < 32:
        raise ValueError("TED_MCP_FORM_SECRET must be set to at least 32 bytes")
    root = Path(env["TED_MCP_PROJECT_ROOT"]) if env.get("TED_MCP_PROJECT_ROOT") else None
    settings = load_settings(env, project_root=root)
    store = OAuthStore(settings.oauth_db_path)
    tools = Tools(settings, Federation(settings))
    return build_app(settings, store, build_server(tools), form_secret=secret)


def main() -> None:
    import os

    import uvicorn

    from src.env_loader import load_env

    load_env()
    app = create_app_from_env()
    uvicorn.run(app, host=os.environ.get("TED_MCP_HOST", "127.0.0.1"),
                port=int(os.environ.get("TED_MCP_PORT", "8087")), log_level="info")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_server.py tests/test_mcp_oauth_flow.py tests/test_mcp_http_app.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server/tools.py src/mcp_server/server.py src/mcp_server/http_app.py tests/test_mcp_server.py
git commit -m "feat(ted-mcp): FastMCP sunucusu, kimlik denetimli edupedia_durum ve süreç girişi

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 8: `edupedia_rehber` — vendored rehberden sınırlı parçalar ve arama

**Files:**
- Create: `src/mcp_server/rehber.py`
- Modify: `src/mcp_server/tools.py` (add `Tools.rehber`)
- Modify: `src/mcp_server/server.py` (register `edupedia_rehber`)
- Test: `tests/test_mcp_rehber.py`

**Interfaces:**
- Consumes: `vendor_sync.VENDOR_DIR` (vendored `SKILL.md`, `references/*.md`); `server.caller_email(ctx)`.
- Produces:
  - `rehber.PART_MAX_BYTES = 8000`.
  - `rehber.SECTIONS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]]` — bölüm → (dosya, başlık numaraları; boş demet = tüm dosya).
  - `rehber.split_sections(text: str) -> list[tuple[str, str]]` (`## ` başlığına göre; başlık, gövde).
  - `rehber.guide(bolum: str, parca: int = 1, vendor: Path = VENDOR_DIR) -> dict`.
  - `rehber.search(q: str, limit: int = 5, vendor: Path = VENDOR_DIR) -> dict`.
  - `Tools.rehber(bolum: str | None, parca: int, ara: str | None) -> dict`.
  - MCP tool `edupedia_rehber(ctx, bolum: str | None = None, parca: int = 1, ara: str | None = None)`.

Ölçülmüş başlıklar (2026-09-13): `SKILL.md` `## 1.`…`## 15.` (6 Modlar, 7 Kaynak-sadakati, 8 İnşa iş akışı, 9 Etkileşim kataloğu, 10 Carbon token'ları, 11 İkon/SVG, 12 Kalite kapıları, 15 Çocuk güvenliği); referanslar `## <n>.` ya da numarasız (`## Ortak segment alanları`, `## İçindekiler`). Referans toplamı ~313 KB → tek yanıta sığmaz; bölüm + parça ile gezilir. `İçindekiler` bölümleri atlanır.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_rehber.py`:

```python
"""Guide sections from vendored references: mapping integrity, part size, navigation, search."""
import re

import pytest

from src.mcp_server import rehber, vendor_sync


def test_every_mapped_heading_exists_in_vendor():
    for bolum, sources in rehber.SECTIONS.items():
        for filename, numbers in sources:
            text = (vendor_sync.VENDOR_DIR / filename).read_text(encoding="utf-8")
            present = {h for h, _ in rehber.split_sections(text)}
            for number in numbers:
                assert any(re.match(rf"##\s+{re.escape(number)}(\.|\s)", h) for h in present), (bolum, filename, number)


@pytest.mark.parametrize("bolum", sorted(rehber.SECTIONS))
def test_each_section_resolves_to_bounded_parts(bolum):
    first = rehber.guide(bolum)
    assert first["status"] == "ok"
    assert first["toplam_parca"] >= 1
    assert first["metin"].strip()
    for n in range(1, first["toplam_parca"] + 1):
        part = rehber.guide(bolum, parca=n)
        assert len(part["metin"].encode("utf-8")) <= rehber.PART_MAX_BYTES
        assert part["kaynaklar"]


def test_akis_starts_with_build_workflow_and_warns_about_plugin_paths():
    part = rehber.guide("akis")
    assert "İnşa iş akışı" in part["metin"]
    assert "edupedia_derle" in part["uyari"]


def test_part_navigation_and_out_of_range():
    first = rehber.guide("carbon")
    if first["toplam_parca"] > 1:
        assert first["sonraki_parca"] == 2
    bad = rehber.guide("carbon", parca=first["toplam_parca"] + 1)
    assert bad["status"] == "gecersiz_parca"


def test_unknown_section_lists_valid_sections():
    body = rehber.guide("yok-boyle-bolum")
    assert body["status"] == "gecersiz_bolum"
    assert body["bolumler"] == sorted(rehber.SECTIONS)


def test_split_sections_skips_table_of_contents():
    text = "# T\n\n## İçindekiler\n- a\n\n## 1. Bir\nx\n\n## 2. İki\ny\n"
    assert [h for h, _ in rehber.split_sections(text)] == ["## 1. Bir", "## 2. İki"]


def test_search_finds_mcq_segment_and_folds_turkish_case():
    hits = rehber.search("MCQ çoktan seçmeli")
    assert hits["status"] == "ok"
    assert any("mcq" in h["baslik"].lower() for h in hits["sonuclar"])
    upper = rehber.search("İNŞA İŞ AKIŞI")
    assert any("İnşa iş akışı" in h["baslik"] for h in upper["sonuclar"])


def test_search_empty_query():
    assert rehber.search("  ")["status"] == "gecersiz_sorgu"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_rehber.py -v`
Expected: FAIL — `ImportError: cannot import name 'rehber' from 'src.mcp_server'`.

- [ ] **Step 3: Create `src/mcp_server/rehber.py`**

```python
"""Serve the vendored edupedia guide as bounded sections for every web surface (spec §9.1)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.mcp_server.vendor_sync import VENDOR_DIR

PART_MAX_BYTES = 8000
_R = "references/"

# bölüm → ((file, heading numbers), ...); an empty tuple means the whole file.
SECTIONS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "akis": (("SKILL.md", ("8",)), (_R + "module-architecture.md", ("3", "4")), (_R + "curriculum-integration.md", ("3",))),
    "modlar": (("SKILL.md", ("3", "6")), (_R + "module-architecture.md", ("1",))),
    "segmentler": ((_R + "module-architecture.md", ("2",)), (_R + "interaction-patterns.md", ())),
    "etkilesim": (("SKILL.md", ("9",)), (_R + "gamified-flows.md", ("2", "3", "4"))),
    "pedagoji": (("SKILL.md", ("4",)), (_R + "adhd-pedagogy.md", ("2", "3", "6", "7", "9"))),
    "carbon": (("SKILL.md", ("10",)), (_R + "carbon-child-system.md", ()), (_R + "carbon-excellence.md", ("2", "4")),
               (_R + "color-system.md", ())),
    "svg": (("SKILL.md", ("11",)), (_R + "svg-authoring.md", ()), (_R + "icon-pictogram-svg.md", ())),
    "ses": ((_R + "audio-system.md", ()),),
    "mufredat": (("SKILL.md", ("7",)), (_R + "curriculum-integration.md", ())),
    "soru": ((_R + "newgen-question-design.md", ()),),
    "sinav": ((_R + "exam-solving.md", ()),),
    "zenginlestirme": ((_R + "content-enrichment.md", ()), (_R + "carbon-sources.md", ())),
    "kalite": (("SKILL.md", ("12", "15")), (_R + "carbon-excellence.md", ("3",)), (_R + "gamified-flows.md", ("5",)),
               (_R + "svg-authoring.md", ("6",))),
}

UYARI = (
    "Bu rehber Claude Code plugin'i için yazıldı. Dosya yolu, script çalıştırma (validate_module.py) ve "
    "yerel teslim adımlarını UYGULAMA: HTML'i kendin yazma; MODULE_DATA'yı edupedia_derle ile derlet, "
    "edupedia_yayinla ile yayınla. Müfredat adımları için edupedia_kapsam ve edupedia_kaynak_oku kullan."
)

_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_NUMBER = re.compile(r"^##\s+(\d+(?:\.\d+)?)")


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = m.group(0).strip()
        if _fold(heading).startswith("## içindekiler"):
            continue
        out.append((heading, text[m.end():end].strip()))
    return out


def _matches(heading: str, numbers: tuple[str, ...]) -> bool:
    if not numbers:
        return True
    m = _NUMBER.match(heading)
    if not m:
        return False
    value = m.group(1)
    return any(value == n or value.startswith(n + ".") for n in numbers)


def _blocks(bolum: str, vendor: Path) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for filename, numbers in SECTIONS[bolum]:
        text = (vendor / filename).read_text(encoding="utf-8")
        for heading, body in split_sections(text):
            if _matches(heading, numbers):
                blocks.append((f"{filename} {heading}", f"{heading}\n\n{body}\n"))
    return blocks


def _pieces(block: str) -> list[str]:
    """Split one oversized block on paragraph, then hard byte boundaries."""
    if len(block.encode("utf-8")) <= PART_MAX_BYTES:
        return [block]
    pieces, current = [], ""
    for para in block.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate.encode("utf-8")) <= PART_MAX_BYTES:
            current = candidate
            continue
        if current:
            pieces.append(current)
        while len(para.encode("utf-8")) > PART_MAX_BYTES:
            cut = para.encode("utf-8")[:PART_MAX_BYTES].decode("utf-8", errors="ignore")
            pieces.append(cut)
            para = para[len(cut):]
        current = para
    if current:
        pieces.append(current)
    return pieces


def _parts(bolum: str, vendor: Path) -> list[tuple[str, list[str]]]:
    parts: list[tuple[str, list[str]]] = []
    text, sources = "", []
    for source, block in _blocks(bolum, vendor):
        for piece in _pieces(block):
            if text and len((text + "\n" + piece).encode("utf-8")) > PART_MAX_BYTES:
                parts.append((text, sources))
                text, sources = "", []
            text = f"{text}\n{piece}" if text else piece
            if source not in sources:
                sources.append(source)
    if text:
        parts.append((text, sources))
    return parts


def guide(bolum: str, parca: int = 1, vendor: Path = VENDOR_DIR) -> dict[str, Any]:
    if bolum not in SECTIONS:
        return {"status": "gecersiz_bolum", "bolumler": sorted(SECTIONS), "mcp_verified": False}
    parts = _parts(bolum, vendor)
    if parca < 1 or parca > len(parts):
        return {"status": "gecersiz_parca", "bolum": bolum, "toplam_parca": len(parts), "mcp_verified": False}
    text, sources = parts[parca - 1]
    body: dict[str, Any] = {
        "status": "ok", "bolum": bolum, "parca": parca, "toplam_parca": len(parts),
        "metin": text, "kaynaklar": sources, "uyari": UYARI, "mcp_verified": False,
    }
    if parca < len(parts):
        body["sonraki_parca"] = parca + 1
    return body


def search(q: str, limit: int = 5, vendor: Path = VENDOR_DIR) -> dict[str, Any]:
    terms = [t for t in re.findall(r"\w+", _fold(q or "")) if len(t) >= 3]
    if not terms:
        return {"status": "gecersiz_sorgu", "mcp_verified": False}
    owners: dict[str, list[str]] = {}
    for bolum, sources in SECTIONS.items():
        for filename, _ in sources:
            owners.setdefault(filename, []).append(bolum)
    scored = []
    files = ["SKILL.md", *sorted(str(p.relative_to(vendor)) for p in (vendor / "references").glob("*.md"))]
    for filename in files:
        for heading, body in split_sections((vendor / filename).read_text(encoding="utf-8")):
            h, b = _fold(heading), _fold(body)
            score = sum(3 * h.count(t) + b.count(t) for t in terms)
            if score:
                scored.append((score, filename, heading, body))
    scored.sort(key=lambda row: -row[0])
    return {
        "status": "ok",
        "sorgu": q,
        "sonuclar": [
            {"kaynak": f, "baslik": h, "bolumler": owners.get(f, []), "ozet": b[:400]}
            for _, f, h, b in scored[:limit]
        ],
        "uyari": UYARI,
        "mcp_verified": False,
    }
```

- [ ] **Step 4: Add `Tools.rehber` to `src/mcp_server/tools.py`**

Add `from src.mcp_server import rehber` to the imports (next to `gates, vendor_sync`) and this method to `Tools`:

```python
    def rehber(self, bolum: str | None = None, parca: int = 1, ara: str | None = None) -> dict[str, Any]:
        if ara:
            return rehber.search(ara)
        return rehber.guide(bolum or "akis", parca=parca)
```

- [ ] **Step 5: Register the tool in `src/mcp_server/server.py`**

Inside `build_server`, after `edupedia_durum`:

```python
    @mcp.tool(annotations=_RO)
    def edupedia_rehber(ctx: Context, bolum: str | None = None, parca: int = 1, ara: str | None = None) -> dict[str, Any]:
        """edupedia üretim rehberi. bolum: akis, modlar, segmentler, etkilesim, pedagoji, carbon, svg, ses,
        mufredat, soru, sinav, zenginlestirme, kalite. Uzun bölümler parca ile gezilir; ara serbest metin arar.
        Her üretime edupedia_rehber('akis') ile başla."""
        caller_email(ctx)
        return tools.rehber(bolum=bolum, parca=parca, ara=ara)
```

Add this test to `tests/test_mcp_server.py` (it reuses that file's `_client`, `_sse_json`, `MCP_HEADERS`, `FULL`, `OAuthStore` names):

```python
def test_rehber_tool_is_registered_and_returns_akis(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    with _client(tmp_path, store) as c:
        r = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                           "params": {"name": "edupedia_rehber", "arguments": {"bolum": "akis"}}},
                             headers={**MCP_HEADERS, "authorization": f"Bearer {key}"}))
    body = json.loads(r["result"]["content"][0]["text"])
    assert body["bolum"] == "akis" and body["status"] == "ok"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_rehber.py tests/test_mcp_server.py -v`
Expected: all PASS. If `test_every_mapped_heading_exists_in_vendor` fails, the vendored references were renumbered upstream: fix the numbers in `SECTIONS` (never loosen the test).

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server/rehber.py src/mcp_server/tools.py src/mcp_server/server.py tests/test_mcp_rehber.py tests/test_mcp_server.py
git commit -m "feat(ted-mcp): edupedia_rehber — vendored rehberden 8 KB'lık bölüm parçaları ve arama

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 9: `edupedia_baglam` — dashboard loopback API'sinden yaklaşan sınav ve ödevler

**Files:**
- Create: `src/mcp_server/dashboard_context.py`
- Modify: `src/mcp_server/tools.py` (add `Tools.baglam`; constructor accepts `dashboard`)
- Modify: `src/mcp_server/server.py` (register `edupedia_baglam`)
- Modify: `src/mcp_server/http_app.py` (`create_app_from_env` passes a `DashboardContext`)
- Test: `tests/test_mcp_baglam.py`

**Interfaces:**
- Consumes: dashboard endpoints (spec §12b), all `require_auth` + `tdyK_` bearer:
  - `GET /api/exams` → `{"exams": [{"id", "course", "title", "examNumber", "date": ISO | None, "status": "upcoming" | "past", …}], "stats": {…}}`
  - `GET /api/homework` → `{"summary", "homework": [{"Ders Adı", "Ödev Başlığı", "Ödev Son Teslim Tarihi", "Ödev Durumu", "normalized_course", "student_marked_done", …}]}`
  - `GET /api/student/profile` → `{"name", "student_no", "class_name", "branch", "photo_data_url", "fields", "scraped_at", "auth"}`
- Produces:
  - `dashboard_context.DashboardUnavailable(Exception)` (`.reason`).
  - `dashboard_context.DashboardContext(base_url: str, api_key: str, session: Any = None, timeout: float = 10.0, clock: Callable[[], float] = time.time)` with `upcoming(gun: int) -> dict` returning `{"sinif_adi", "sinif_duzeyi", "sube", "sinavlar": [...], "odevler": [...], "tarihsiz_sinav_sayisi"}`.
  - `Tools.__init__(settings, federation, clock=time.time, dashboard: DashboardContext | None = None)`; `Tools.baglam(email: str, gun: int = 7) -> dict`.
  - MCP tool `edupedia_baglam(ctx, gun: int = 7)`.

Gizlilik kuralı (spec §6.4): yanıt öğrenci adını, numarasını, fotoğrafını ve portal alanlarını **taşımaz**; yalnız sınıf düzeyi, şube, ders/konu/tarih. Sınav öğesi `{"id", "ders", "baslik", "sinav_no", "tarih": "YYYY-MM-DD"}`; ödev öğesi `{"id", "ders", "baslik", "son_teslim": "YYYY-MM-DDTHH:MM" | None, "durum"}` (`id` = `sha1(ders|baslik|son_teslim)[:12]`, ileride `ted_link` için kararlı).

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_baglam.py`:

```python
"""edupedia_baglam: upcoming exams/homework from the dashboard loopback API, privacy-filtered."""
from datetime import datetime

import pytest
import requests

from src.mcp_server import tools as tools_mod
from src.mcp_server.config import load_settings
from src.mcp_server.dashboard_context import DashboardContext, DashboardUnavailable

NOW = datetime(2026, 9, 14, 9, 0).timestamp()  # Monday
FULL = "drmahirkurt@gmail.com"

EXAMS = {"exams": [
    {"id": "e1", "course": "Fen Bilimleri", "title": "1. Yazılı", "examNumber": 1, "date": "2026-09-18T00:00:00", "status": "upcoming"},
    {"id": "e2", "course": "Matematik", "title": "2. Yazılı", "examNumber": 2, "date": "2026-10-20T00:00:00Z", "status": "upcoming"},
    {"id": "e3", "course": "Türkçe", "title": "Sınav", "examNumber": None, "date": None, "status": "upcoming"},
    {"id": "e4", "course": "Fen Bilimleri", "title": "Eski", "examNumber": 1, "date": "2026-09-01T00:00:00", "status": "past"},
], "stats": {}}
HOMEWORK = {"summary": "", "homework": [
    {"Ders Adı": "FEN BİLİMLERİ", "normalized_course": "Fen Bilimleri", "Ödev Başlığı": "Madde döngüsü",
     "Ödev Son Teslim Tarihi": "16.09.2026 23:59", "Ödev Durumu": "Teslim edilmedi", "student_marked_done": False},
    {"Ders Adı": "MATEMATİK", "Ödev Başlığı": "Kesirler", "Ödev Son Teslim Tarihi": "2026-09-15T18:00:00",
     "Ödev Durumu": "Teslim edilmedi", "student_marked_done": True},
    {"Ders Adı": "TÜRKÇE", "Ödev Başlığı": "Okuma", "Ödev Son Teslim Tarihi": "30.10.2026", "Ödev Durumu": "", "student_marked_done": False},
]}
PROFILE = {"name": "Işık Kurt", "student_no": "123", "class_name": "5-A", "branch": "A",
           "photo_data_url": "data:image/png;base64,xx", "fields": {"TC": "1"}, "scraped_at": "", "auth": {}}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, routes=None, error=None):
        self.routes = routes or {"/api/exams": Resp(200, EXAMS), "/api/homework": Resp(200, HOMEWORK),
                                 "/api/student/profile": Resp(200, PROFILE)}
        self.error = error
        self.seen = []

    def get(self, url, headers=None, timeout=None):
        self.seen.append((url, headers, timeout))
        if self.error:
            raise self.error
        return self.routes[url.split("127.0.0.1:8085", 1)[1]]


def _ctx(session):
    return DashboardContext("http://127.0.0.1:8085", "tdyK_test", session=session, clock=lambda: NOW)


def test_upcoming_filters_window_and_done_items():
    body = _ctx(FakeSession()).upcoming(7)
    assert [e["id"] for e in body["sinavlar"]] == ["e1"]
    assert body["sinavlar"][0] == {"id": "e1", "ders": "Fen Bilimleri", "baslik": "1. Yazılı", "sinav_no": 1, "tarih": "2026-09-18"}
    assert body["tarihsiz_sinav_sayisi"] == 1
    assert [o["baslik"] for o in body["odevler"]] == ["Madde döngüsü"]
    assert body["odevler"][0]["ders"] == "Fen Bilimleri"
    assert body["odevler"][0]["son_teslim"] == "2026-09-16T23:59"
    assert len(body["odevler"][0]["id"]) == 12


def test_upcoming_longer_window_includes_later_items():
    body = _ctx(FakeSession()).upcoming(60)
    assert {e["id"] for e in body["sinavlar"]} == {"e1", "e2"}
    assert {o["baslik"] for o in body["odevler"]} == {"Madde döngüsü", "Okuma"}


def test_profile_is_reduced_to_grade_and_branch():
    body = _ctx(FakeSession()).upcoming(7)
    assert body["sinif_adi"] == "5-A" and body["sinif_duzeyi"] == 5 and body["sube"] == "A"
    flat = repr(body)
    for secret in ("Işık Kurt", "123", "base64", "TC"):
        assert secret not in flat


def test_sends_bearer_to_loopback_with_timeout():
    session = FakeSession()
    _ctx(session).upcoming(7)
    url, headers, timeout = session.seen[0]
    assert url.startswith("http://127.0.0.1:8085/api/")
    assert headers["Authorization"] == "Bearer tdyK_test"
    assert timeout == 10.0


def test_http_error_and_network_error_are_unavailable():
    with pytest.raises(DashboardUnavailable) as exc:
        _ctx(FakeSession(routes={"/api/exams": Resp(401, {}), "/api/homework": Resp(200, HOMEWORK),
                                 "/api/student/profile": Resp(200, PROFILE)})).upcoming(7)
    assert exc.value.reason == "http_401"
    with pytest.raises(DashboardUnavailable) as exc:
        _ctx(FakeSession(error=requests.ConnectionError("down"))).upcoming(7)
    assert exc.value.reason == "unreachable"


class NoFed:
    def configured(self, server):
        return False


def test_tools_baglam_degrades_without_key_and_clamps_window(tmp_path):
    settings = load_settings({}, project_root=tmp_path)
    t = tools_mod.Tools(settings, NoFed(), dashboard=None)
    body = t.baglam(FULL, gun=7)
    assert body["status"] == "degraded" and body["coverage"] == {"tedy-dashboard": "skipped:anahtar yok"}

    settings = load_settings({"TED_DASHBOARD_API_KEY": "tdyK_test"}, project_root=tmp_path)
    t = tools_mod.Tools(settings, NoFed(), dashboard=_ctx(FakeSession()))
    body = t.baglam(FULL, gun=500)
    assert body["status"] == "ok" and body["gun"] == 60
    assert body["coverage"] == {"tedy-dashboard": "hit"}
    assert body["mcp_verified"] is False and body["caveat"]

    t = tools_mod.Tools(settings, NoFed(), dashboard=_ctx(FakeSession(error=requests.Timeout("slow"))))
    body = t.baglam(FULL)
    assert body["status"] == "degraded" and body["coverage"] == {"tedy-dashboard": "degraded:unreachable"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_baglam.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mcp_server.dashboard_context'`.

- [ ] **Step 3: Create `src/mcp_server/dashboard_context.py`**

```python
"""Read Işık's upcoming exams and homework through the dashboard's own loopback API.

The exam list is derived inside /api/exams (calendar + grade table + content map), so the
orchestrator reuses that endpoint instead of duplicating ~200 lines (spec §12b). Output is
privacy-reduced: no name, student number, photo or raw portal fields.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable

import requests


class DashboardUnavailable(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_DUE_FORMATS = ("%d.%m.%Y %H:%M", "%d.%m.%Y")


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _parse_due(value: Any) -> datetime | None:
    text = str(value or "").strip()
    for fmt in _DUE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return _parse_iso(text)


def _grade_level(class_name: str) -> int | None:
    m = re.search(r"\b(1[0-2]|[1-9])\b", class_name or "")
    return int(m.group(1)) if m else None


class DashboardContext:
    def __init__(self, base_url: str, api_key: str, session: Any = None, timeout: float = 10.0,
                 clock: Callable[[], float] = time.time) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = session if session is not None else requests.Session()
        self.timeout = timeout
        self.clock = clock

    def _get(self, path: str) -> dict[str, Any]:
        try:
            resp = self.session.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}", "User-Agent": "ted-mcp/0.1"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise DashboardUnavailable("unreachable") from exc
        if resp.status_code != 200:
            raise DashboardUnavailable(f"http_{resp.status_code}")
        try:
            body = resp.json()
        except ValueError as exc:
            raise DashboardUnavailable("undecodable") from exc
        if not isinstance(body, dict):
            raise DashboardUnavailable("unexpected_shape")
        return body

    def upcoming(self, gun: int) -> dict[str, Any]:
        today = datetime.fromtimestamp(self.clock()).date()
        until = today + timedelta(days=gun)
        exams = self._get("/api/exams").get("exams") or []
        homework = self._get("/api/homework").get("homework") or []
        profile = self._get("/api/student/profile")

        sinavlar, undated = [], 0
        for exam in exams:
            if not isinstance(exam, dict) or exam.get("status") != "upcoming":
                continue
            when = _parse_iso(exam.get("date"))
            if when is None:
                undated += 1
                continue
            if today <= when.date() <= until:
                sinavlar.append({"id": exam.get("id"), "ders": exam.get("course"), "baslik": exam.get("title"),
                                 "sinav_no": exam.get("examNumber"), "tarih": when.date().isoformat()})
        sinavlar.sort(key=lambda e: e["tarih"])

        odevler = []
        for row in homework:
            if not isinstance(row, dict) or row.get("student_marked_done"):
                continue
            due = _parse_due(row.get("Ödev Son Teslim Tarihi"))
            if due is None or not (today <= due.date() <= until):
                continue
            ders = row.get("normalized_course") or row.get("Ders Adı") or ""
            baslik = row.get("Ödev Başlığı") or ""
            son = due.strftime("%Y-%m-%dT%H:%M")
            odevler.append({
                "id": hashlib.sha1(f"{ders}|{baslik}|{son}".encode("utf-8")).hexdigest()[:12],
                "ders": ders, "baslik": baslik, "son_teslim": son, "durum": row.get("Ödev Durumu") or "",
            })
        odevler.sort(key=lambda o: o["son_teslim"])

        class_name = str(profile.get("class_name") or "")
        return {
            "sinif_adi": class_name,
            "sinif_duzeyi": _grade_level(class_name),
            "sube": profile.get("branch") or "",
            "sinavlar": sinavlar,
            "odevler": odevler,
            "tarihsiz_sinav_sayisi": undated,
        }
```

- [ ] **Step 4: Add `Tools.baglam` and the `dashboard` dependency in `src/mcp_server/tools.py`**

Add `from src.mcp_server.dashboard_context import DashboardContext, DashboardUnavailable` to the imports. Replace the `Tools.__init__` signature and body with:

```python
    def __init__(self, settings: Settings, federation: Federation, clock: Callable[[], float] = time.time,
                 dashboard: DashboardContext | None = None) -> None:
        self.settings = settings
        self.federation = federation
        self.clock = clock
        self.dashboard = dashboard
```

Add the method:

```python
    def baglam(self, email: str, gun: int = 7) -> dict[str, Any]:
        gun = max(1, min(int(gun), 60))
        base: dict[str, Any] = {
            "gun": gun,
            "caveat": "Veriler okul portalından 15 dakikada bir çekilir; yeni duyurulan sınav veya ödev eksik olabilir.",
            "mcp_verified": False,
        }
        if self.dashboard is None or not self.settings.dashboard_api_key:
            return {**base, "status": "degraded", "coverage": {"tedy-dashboard": "skipped:anahtar yok"}}
        try:
            data = self.dashboard.upcoming(gun)
        except DashboardUnavailable as exc:
            return {**base, "status": "degraded", "coverage": {"tedy-dashboard": f"degraded:{exc.reason}"}}
        state = "hit" if (data["sinavlar"] or data["odevler"]) else "empty"
        return {**base, "status": "ok", **data, "coverage": {"tedy-dashboard": state}}
```

- [ ] **Step 5: Register the tool and wire the dashboard client**

In `src/mcp_server/server.py`, inside `build_server` after `edupedia_rehber`:

```python
    @mcp.tool(annotations=_RO)
    def edupedia_baglam(ctx: Context, gun: int = 7) -> dict[str, Any]:
        """TEDY'den önümüzdeki gün sayısı (1-60) içindeki sınav ve ödevleri, sınıf düzeyini döner.
        Öğrenci adı ve kişisel alanlar dönmez. Konu seçerken bu listeyi kullan."""
        return tools.baglam(caller_email(ctx), gun=gun)
```

In `src/mcp_server/http_app.py` `create_app_from_env`, add the import `from src.mcp_server.dashboard_context import DashboardContext` and replace `tools = Tools(settings, Federation(settings))` with:

```python
    dashboard = DashboardContext(settings.dashboard_api_url, settings.dashboard_api_key)
    tools = Tools(settings, Federation(settings), dashboard=dashboard)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_baglam.py tests/test_mcp_server.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server/dashboard_context.py src/mcp_server/tools.py src/mcp_server/server.py src/mcp_server/http_app.py tests/test_mcp_baglam.py
git commit -m "feat(ted-mcp): edupedia_baglam — dashboard loopback API'sinden gizlilik süzgeçli sınav/ödev bağlamı

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 10: Çalıştırma kaydı ve müfredat doğrulama (ders, sınıf, kazanım)

**Files:**
- Create: `src/mcp_server/runs.py`
- Create: `src/mcp_server/kapsam.py` (doğrulama katmanı; Task 11 derlemeyi ekler)
- Test: `tests/test_mcp_kapsam_dogrulama.py`

**Interfaces:**
- Consumes: `federation.Federation.call(server, tool, args, beklenen)`, `federation.FederationError`, `federation.MUFREDAT`, `src.json_utils.atomic_json_dump(data, path)`.
- maarif-mufredat contracts (server.py, 0.4.1):
  - `list_subjects(level=None, q=None) -> list[{slug, name, level, grade_count}]` → `beklenen="liste"`
  - `search_learning_outcomes(q, level=None, subject=None, grade=None, limit=20, distinct_codes=False) -> {results: [{code, text, subject, grade, document_id, page_no, fragment_type}], included_fragment_types}` → `beklenen="nesne"`
  - Subject identity is the **slug** (`fen-bilimleri-dersi`); grade strings are `"5.Sınıf"`.
- Produces:
  - `runs.RUN_ID_RE = re.compile(r"^[0-9a-f]{12}$")`.
  - `runs.RunStore(data_dir: Path)` with `new_id() -> str`, `save(run_id: str, record: dict) -> None`, `load(run_id: str) -> dict | None`, `save_page(run_id: str, document_id: int, page_no: int, text: str) -> None`, `pages(run_id: str) -> list[dict]` (`{"document_id", "page_no", "text"}` sorted).
  - `kapsam.normalize_grade(sinif: str | int) -> str | None` (`"5"`, `5`, `"5. sınıf"`, `"5.Sınıf"` → `"5.Sınıf"`; 1–12 dışı → `None`).
  - `kapsam.KapsamError(Exception)` (`.status: str`, `.detay: dict`).
  - `kapsam.resolve_subject(federation, ders: str) -> dict` (`{"slug", "name"}`; raises `KapsamError("ders_bulunamadi" | "belirsiz_ders" | "manual_required")`).
  - `kapsam.verify_outcomes(federation, slug: str, grade: str, konu: str | None, kazanim_kodu: str | None) -> dict` → `{"kazanimlar": [...], "uyusmazlik": [...]}` (raises `KapsamError("konu_veya_kazanim_gerekli" | "kazanim_dogrulanamadi" | "manual_required")`).

Sözleşme kuralı (edupedia içerik sözleşmesi): sınıf ve ders koddan **çıkarılmaz**; otorite mufredat'ın döndürdüğü `subject` + `grade`'dir. Kullanıcının verdiği ile MCP'nin döndürdüğü farklıysa `uyusmazlik` listesine yazılır ve MCP değeri kullanılır.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_kapsam_dogrulama.py`:

```python
"""Run store and curriculum verification (subject slug, grade, outcome authority)."""
import json

import pytest

from src.mcp_server import kapsam
from src.mcp_server.federation import FederationError
from src.mcp_server.runs import RUN_ID_RE, RunStore


class FakeFed:
    def __init__(self, responses, fail=()):
        self.responses = responses
        self.fail = set(fail)
        self.calls = []

    def configured(self, server):
        return True

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool, args, beklenen))
        if (server, tool) in self.fail:
            raise FederationError(server, tool, "timeout")
        value = self.responses[(server, tool)]
        return value(args) if callable(value) else value


SUBJECTS = [
    {"slug": "fen-bilimleri-dersi", "name": "Fen Bilimleri Dersi", "level": "temel-egitim", "grade_count": 6},
    {"slug": "fen-lisesi-fizik", "name": "Fizik (Fen Lisesi)", "level": "ortaogretim", "grade_count": 4},
]


def test_run_store_round_trip(tmp_path):
    store = RunStore(tmp_path)
    run_id = store.new_id()
    assert RUN_ID_RE.match(run_id)
    store.save(run_id, {"created_by": "a@b", "ders": "x"})
    assert store.load(run_id) == {"created_by": "a@b", "ders": "x"}
    store.save_page(run_id, 197, 113, "ikinci")
    store.save_page(run_id, 197, 112, "birinci")
    assert store.pages(run_id) == [
        {"document_id": 197, "page_no": 112, "text": "birinci"},
        {"document_id": 197, "page_no": 113, "text": "ikinci"},
    ]
    assert store.load("../etc") is None
    assert store.load("ffffffffffff") is None
    assert json.loads((tmp_path / "edupedia_runs" / run_id / "run.json").read_text(encoding="utf-8"))["ders"] == "x"


@pytest.mark.parametrize("raw,expected", [
    ("5", "5.Sınıf"), (5, "5.Sınıf"), ("5. sınıf", "5.Sınıf"), ("5.Sınıf", "5.Sınıf"), ("12", "12.Sınıf"),
    ("0", None), ("13", None), ("beşinci", None), ("", None),
])
def test_normalize_grade(raw, expected):
    assert kapsam.normalize_grade(raw) == expected


def test_resolve_subject_exact_name_wins_over_partial():
    fed = FakeFed({("maarif-mufredat", "list_subjects"): SUBJECTS})
    assert kapsam.resolve_subject(fed, "Fen Bilimleri") == {"slug": "fen-bilimleri-dersi", "name": "Fen Bilimleri Dersi"}
    assert fed.calls[0][2] == {"q": "Fen Bilimleri"} and fed.calls[0][3] == "liste"


def test_resolve_subject_accepts_slug_and_reports_ambiguity_and_absence():
    fed = FakeFed({("maarif-mufredat", "list_subjects"): SUBJECTS})
    assert kapsam.resolve_subject(fed, "fen-lisesi-fizik")["slug"] == "fen-lisesi-fizik"
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(fed, "fen")
    assert exc.value.status == "belirsiz_ders"
    assert {c["slug"] for c in exc.value.detay["adaylar"]} == {"fen-bilimleri-dersi", "fen-lisesi-fizik"}
    empty = FakeFed({("maarif-mufredat", "list_subjects"): []})
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(empty, "Astroloji")
    assert exc.value.status == "ders_bulunamadi"


def test_resolve_subject_federation_failure_is_manual_required():
    fed = FakeFed({}, fail={("maarif-mufredat", "list_subjects")})
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.resolve_subject(fed, "Fen Bilimleri")
    assert exc.value.status == "manual_required"
    assert exc.value.detay["neden"] == "timeout"


def _slo(results):
    return {("maarif-mufredat", "search_learning_outcomes"): {"results": results, "included_fragment_types": ["outcome"]}}


def test_verify_outcomes_by_code_uses_mcp_authority_and_reports_mismatch():
    row = {"code": "FB.6.3.1.1", "text": "Fotosentez…", "subject": "fen-bilimleri-dersi", "grade": "6.Sınıf",
           "document_id": 50, "page_no": 12, "fragment_type": "outcome"}
    fed = FakeFed(_slo([row, {**row, "code": "FB.6.3.1.2"}]))
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.6.3.1.1")
    assert [k["code"] for k in out["kazanimlar"]] == ["FB.6.3.1.1"]
    assert out["uyusmazlik"] == [{"alan": "sinif", "verilen": "5.Sınıf", "mufredat": "6.Sınıf"}]
    assert fed.calls[0][2] == {"q": "FB.6.3.1.1", "subject": "fen-bilimleri-dersi", "limit": 10, "distinct_codes": True}


def test_verify_outcomes_code_not_found():
    fed = FakeFed(_slo([{"code": "FB.5.1.1.1", "text": "x", "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
                         "document_id": 1, "page_no": 1, "fragment_type": "outcome"}]))
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", None, "FB.9.9.9.9")
    assert exc.value.status == "kazanim_dogrulanamadi"


def test_verify_outcomes_by_topic_filters_grade_and_trims_text():
    long_text = "a" * 900
    fed = FakeFed(_slo([
        {"code": "FB.5.4.1.1", "text": long_text, "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
         "document_id": 7, "page_no": 30, "fragment_type": "outcome"},
    ]))
    out = kapsam.verify_outcomes(fed, "fen-bilimleri-dersi", "5.Sınıf", "maddenin halleri", None)
    assert out["kazanimlar"][0]["code"] == "FB.5.4.1.1"
    assert len(out["kazanimlar"][0]["text"]) == 400
    assert fed.calls[0][2] == {"q": "maddenin halleri", "subject": "fen-bilimleri-dersi", "grade": "5.Sınıf",
                               "limit": 8, "distinct_codes": True}


def test_verify_outcomes_requires_topic_or_code():
    with pytest.raises(kapsam.KapsamError) as exc:
        kapsam.verify_outcomes(FakeFed({}), "fen-bilimleri-dersi", "5.Sınıf", None, None)
    assert exc.value.status == "konu_veya_kazanim_gerekli"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_kapsam_dogrulama.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mcp_server.runs'`.

- [ ] **Step 3: Create `src/mcp_server/runs.py`**

```python
"""Per-run scratch record: output/edupedia_runs/<run_id>/ (git-ignored, never shipped to the fleet)."""
from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Any

from src.json_utils import atomic_json_dump

RUN_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_PAGE_RE = re.compile(r"^(\d+)-(\d+)\.txt$")


class RunStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = Path(data_dir) / "edupedia_runs"

    def new_id(self) -> str:
        return secrets.token_hex(6)

    def _dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.match(run_id or ""):
            raise ValueError("invalid run_id")
        return self.root / run_id

    def save(self, run_id: str, record: dict[str, Any]) -> None:
        atomic_json_dump(record, str(self._dir(run_id) / "run.json"))

    def load(self, run_id: str) -> dict[str, Any] | None:
        try:
            path = self._dir(run_id) / "run.json"
        except ValueError:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def save_page(self, run_id: str, document_id: int, page_no: int, text: str) -> None:
        pages = self._dir(run_id) / "pages"
        pages.mkdir(parents=True, exist_ok=True)
        (pages / f"{int(document_id)}-{int(page_no)}.txt").write_text(text, encoding="utf-8")

    def pages(self, run_id: str) -> list[dict[str, Any]]:
        try:
            folder = self._dir(run_id) / "pages"
        except ValueError:
            return []
        rows = []
        for path in folder.glob("*.txt") if folder.is_dir() else []:
            m = _PAGE_RE.match(path.name)
            if m:
                rows.append({"document_id": int(m.group(1)), "page_no": int(m.group(2)),
                             "text": path.read_text(encoding="utf-8")})
        return sorted(rows, key=lambda r: (r["document_id"], r["page_no"]))
```

- [ ] **Step 4: Create `src/mcp_server/kapsam.py` (verification layer)**

```python
"""edupedia_kapsam: verify subject/grade/outcomes against maarif-mufredat, then frame the module.

Contract (edupedia content contract): grade and subject are never inferred from an outcome
code; the authority is what maarif-mufredat returns. Task 11 adds textbook, figures, OER and
anamnesis ingestion on top of this verification layer.
"""
from __future__ import annotations

import re
from typing import Any

from src.mcp_server.federation import MUFREDAT, Federation, FederationError

OUTCOME_TEXT_MAX = 400


class KapsamError(Exception):
    def __init__(self, status: str, **detay: Any) -> None:
        super().__init__(status)
        self.status = status
        self.detay = detay


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower().strip()


def normalize_grade(sinif: str | int) -> str | None:
    m = re.search(r"\d+", str(sinif))
    if not m:
        return None
    n = int(m.group(0))
    return f"{n}.Sınıf" if 1 <= n <= 12 else None


def _mufredat(federation: Federation, tool: str, args: dict[str, Any], beklenen: str) -> Any:
    try:
        return federation.call(MUFREDAT, tool, args, beklenen=beklenen)
    except FederationError as exc:
        raise KapsamError("manual_required", sunucu=MUFREDAT, arac=tool, neden=exc.reason) from exc


def resolve_subject(federation: Federation, ders: str) -> dict[str, str]:
    subjects = _mufredat(federation, "list_subjects", {"q": ders}, "liste")
    wanted = _fold(ders)
    for s in subjects:
        if s.get("slug") == ders.strip():
            return {"slug": s["slug"], "name": s["name"]}
    exact = [s for s in subjects if _fold(s.get("name", "")) in (wanted, f"{wanted} dersi")]
    if len(exact) == 1:
        return {"slug": exact[0]["slug"], "name": exact[0]["name"]}
    if len(subjects) == 1:
        return {"slug": subjects[0]["slug"], "name": subjects[0]["name"]}
    if not subjects:
        raise KapsamError("ders_bulunamadi", ders=ders)
    raise KapsamError("belirsiz_ders", ders=ders,
                      adaylar=[{"slug": s["slug"], "name": s["name"], "level": s.get("level")} for s in subjects[:10]])


def _outcome(row: dict[str, Any]) -> dict[str, Any]:
    return {"code": row.get("code"), "text": (row.get("text") or "")[:OUTCOME_TEXT_MAX],
            "subject": row.get("subject"), "grade": row.get("grade"),
            "document_id": row.get("document_id"), "page_no": row.get("page_no")}


def verify_outcomes(federation: Federation, slug: str, grade: str, konu: str | None,
                    kazanim_kodu: str | None) -> dict[str, Any]:
    if kazanim_kodu:
        body = _mufredat(federation, "search_learning_outcomes",
                         {"q": kazanim_kodu, "subject": slug, "limit": 10, "distinct_codes": True}, "nesne")
        rows = [r for r in body.get("results") or [] if r.get("code") == kazanim_kodu.strip()]
        if not rows:
            raise KapsamError("kazanim_dogrulanamadi", kazanim_kodu=kazanim_kodu, ders=slug)
    elif konu:
        body = _mufredat(federation, "search_learning_outcomes",
                         {"q": konu, "subject": slug, "grade": grade, "limit": 8, "distinct_codes": True}, "nesne")
        rows = [r for r in body.get("results") or [] if r.get("grade") in (None, grade)]
    else:
        raise KapsamError("konu_veya_kazanim_gerekli")
    kazanimlar = [_outcome(r) for r in rows]
    uyusmazlik = []
    if kazanimlar:
        first = kazanimlar[0]
        if first["grade"] and first["grade"] != grade:
            uyusmazlik.append({"alan": "sinif", "verilen": grade, "mufredat": first["grade"]})
        if first["subject"] and first["subject"] != slug:
            uyusmazlik.append({"alan": "ders", "verilen": slug, "mufredat": first["subject"]})
    return {"kazanimlar": kazanimlar, "uyusmazlik": uyusmazlik}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_kapsam_dogrulama.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server/runs.py src/mcp_server/kapsam.py tests/test_mcp_kapsam_dogrulama.py
git commit -m "feat(ted-mcp): çalıştırma kaydı ve müfredat otoriteli ders/sınıf/kazanım doğrulaması

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 11: `edupedia_kapsam` — ders kitabı çerçevesi, figürler, OER ve anamnesis alımı

**Files:**
- Modify: `src/mcp_server/kapsam.py` (append frame builder + `KapsamBuilder`)
- Modify: `src/mcp_server/tools.py` (`runs` dependency, `Tools.kapsam`)
- Modify: `src/mcp_server/server.py` (register `edupedia_kapsam`)
- Test: `tests/test_mcp_kapsam.py`

**Interfaces:**
- Consumes: Task 10 `normalize_grade`, `resolve_subject`, `verify_outcomes`, `KapsamError`, `RunStore`; `Coverage`; `federation.MUFREDAT/EGITIM_KAYNAK/ANAMNESIS`.
- Fleet contracts:
  - mufredat `list_textbooks(subject, grade, limit) -> list[{document_id, kind, subject, grade_or_grades, title, pdf_url, source_url, page_count, level, level_less}]` (`liste`)
  - mufredat `search_figures(query, subject, grade, document_id, limit≤50) -> {query, count, figures: [{figure_id, document_id, page_no, label, caption, snippet, …}]}` (`nesne`)
  - mufredat `get_document_text(document_id, page_range="a-b", max_chars) -> {document, total_pages, returned, truncated, pages: [{page_no, text}]}` or `{error: "invalid_range", …}` (`nesne`; ≤ 25 pages per call)
  - egitim-kaynak `kb_search(q, top_k) -> {status, results: [{doc_id, title, passage, license, quote_allowed, source_url, match_kind, …}]}` (`nesne`)
  - egitim-kaynak `kb_for_outcome(outcome_code, top_k) -> {status: "ok" | "degraded", reason?, results: [...]}` (`nesne`)
  - anamnesis `ingest_document(text, doc_id≤56 bytes, collection, title, source, ttl_hours≤720) -> {doc_id, collection, n_chunks, …}` (`nesne`)
- Produces:
  - `kapsam.PAGE_WINDOW = 6`; `kapsam.anamnesis_doc_id(run_id: str, document_id: int, first: int, last: int) -> str` (≤ 56 bytes).
  - `kapsam.KapsamBuilder(federation: Federation, runs: RunStore, clock: Callable[[], float] = time.time)` with `build(email, ders, sinif, konu=None, kazanim_kodu=None) -> dict`.
  - `Tools.__init__(settings, federation, clock=time.time, dashboard=None, runs: RunStore | None = None)`; `Tools.kapsam(email, ders, sinif, konu=None, kazanim_kodu=None) -> dict`.
  - MCP tool `edupedia_kapsam(ctx, ders: str, sinif: str, konu: str | None = None, kazanim_kodu: str | None = None)`.

Yanıt (`status == "ok"`): `run_id`, `ders {slug, name}`, `sinif`, `kazanimlar`, `uyusmazlik`, `cerceve {kind: "textbook" | "program" | None, document_id, title, sayfalar: "a-b" | None, not?}` (`kind: None` = mufredat kitap adımında düştü, `coverage` `degraded`), `kitap_sayfalari [{page_no, ozet≤400}]`, `figur_adaylari [{figure_id, page_no, etiket, aciklama≤200}]` (≤ 6), `oer [{doc_id, baslik, pasaj, lisans, alinti_izni, kaynak_url, eslesme}]` (≤ 5; `pasaj` 300 karakter, `alinti_izni` false ise 160), `kazanim_eslesmesi?`, `coverage`, `caveat`, `sonraki_adim`, `mcp_verified: false`. Hata durumları `status` ∈ `gecersiz_sinif`, `ders_bulunamadi`, `belirsiz_ders`, `kazanim_dogrulanamadi`, `konu_veya_kazanim_gerekli`, `manual_required` ve `KapsamError.detay` alanlarını taşır; hata durumunda çalıştırma kaydı **oluşturulmaz**.

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_kapsam.py`:

```python
"""edupedia_kapsam end-to-end over a fake federation: frame, pages, figures, OER, anamnesis, run record."""
import pytest

from src.mcp_server import kapsam
from src.mcp_server.federation import FederationError
from src.mcp_server.runs import RunStore

FULL = "drmahirkurt@gmail.com"
SLUG = "fen-bilimleri-dersi"


class FakeFed:
    def __init__(self, responses, configured=("maarif-mufredat", "egitim-kaynak", "anamnesis"), fail=()):
        self.responses, self._configured, self.fail, self.calls = responses, set(configured), set(fail), []

    def configured(self, server):
        return server in self._configured

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool, args, beklenen))
        if (server, tool) in self.fail:
            raise FederationError(server, tool, "timeout")
        return self.responses[(server, tool)]

    def called(self, server, tool):
        return [c for c in self.calls if c[0] == server and c[1] == tool]


OUTCOME = {"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar.", "subject": SLUG, "grade": "5.Sınıf",
           "document_id": 9, "page_no": 40, "fragment_type": "outcome"}


def _responses(**over):
    base = {
        ("maarif-mufredat", "list_subjects"): [{"slug": SLUG, "name": "Fen Bilimleri Dersi", "level": "temel-egitim", "grade_count": 6}],
        ("maarif-mufredat", "search_learning_outcomes"): {"results": [OUTCOME], "included_fragment_types": ["outcome"]},
        ("maarif-mufredat", "list_textbooks"): [
            {"document_id": 196, "title": "Fen 5 (boş)", "page_count": 0},
            {"document_id": 197, "title": "Fen Bilimleri 5", "page_count": 240},
        ],
        ("maarif-mufredat", "search_figures"): {"query": "x", "count": 2, "figures": [
            {"figure_id": 11, "document_id": 197, "page_no": 115, "label": "Görsel 4.2", "caption": "Su döngüsü " * 40},
            {"figure_id": 10, "document_id": 197, "page_no": 112, "label": "Görsel 4.1", "caption": "Katı sıvı gaz"},
        ]},
        ("maarif-mufredat", "get_document_text"): {"document": {"document_id": 197}, "total_pages": 240, "returned": 6,
                                                   "truncated": False, "pages": [{"page_no": p, "text": f"sayfa {p} metni"} for p in range(111, 117)]},
        ("egitim-kaynak", "kb_search"): {"status": "ok", "results": [
            {"doc_id": "phet:states", "title": "Maddenin Hâlleri", "passage": "p" * 500, "license": "CC BY-NC 4.0",
             "quote_allowed": True, "source_url": "https://phet", "match_kind": "text"},
            {"doc_id": "wikipedia-tr:Madde", "title": "Madde", "passage": "w" * 500, "license": "CC BY-SA 4.0",
             "quote_allowed": False, "source_url": "https://wiki", "match_kind": "text"},
        ]},
        ("egitim-kaynak", "kb_for_outcome"): {"status": "degraded", "reason": "interim_low_relevance", "results": []},
        ("anamnesis", "ingest_document"): {"doc_id": "x", "collection": "y", "n_chunks": 3},
    }
    base.update(over)
    return base


def _build(tmp_path, fed, **kw):
    runs = RunStore(tmp_path)
    return kapsam.KapsamBuilder(fed, runs, clock=lambda: 1_800_000_000.0).build(FULL, "Fen Bilimleri", "5", **kw), runs


def test_happy_path_frames_textbook_pages_figures_oer_and_ingests(tmp_path):
    fed = FakeFed(_responses())
    body, runs = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["ders"] == {"slug": SLUG, "name": "Fen Bilimleri Dersi"}
    assert body["cerceve"] == {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"}
    assert fed.called("maarif-mufredat", "get_document_text")[0][2] == {"document_id": 197, "page_range": "111-116", "max_chars": 60000}
    assert [p["page_no"] for p in body["kitap_sayfalari"]] == list(range(111, 117))
    assert [f["figure_id"] for f in body["figur_adaylari"]] == [10, 11]
    assert len(body["figur_adaylari"][1]["aciklama"]) == 200
    assert len(body["oer"][0]["pasaj"]) == 300 and len(body["oer"][1]["pasaj"]) == 160
    assert body["oer"][1]["alinti_izni"] is False

    ingest = fed.called("anamnesis", "ingest_document")[0][2]
    assert ingest["collection"] == f"edupedia:run:{body['run_id']}"
    assert ingest["doc_id"] == f"edupedia:{body['run_id']}:kitap/197/111-116"
    assert len(ingest["doc_id"].encode()) <= 56
    assert "=== Sayfa 111 ===" in ingest["text"] and ingest["ttl_hours"] == 168

    assert body["coverage"] == {"maarif-mufredat": "hit", "egitim-kaynak": "hit", "anamnesis": "hit"}
    record = runs.load(body["run_id"])
    assert record["created_by"] == FULL and record["cerceve"]["document_id"] == 197
    assert len(runs.pages(body["run_id"])) == 6
    assert body["mcp_verified"] is False and body["caveat"] and body["sonraki_adim"]


def test_anamnesis_failure_degrades_but_keeps_local_pages(tmp_path):
    fed = FakeFed(_responses(), fail={("anamnesis", "ingest_document")})
    body, runs = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["coverage"]["anamnesis"] == "degraded:timeout"
    assert len(runs.pages(body["run_id"])) == 6


def test_anamnesis_unconfigured_is_skipped(tmp_path):
    fed = FakeFed(_responses(), configured=("maarif-mufredat", "egitim-kaynak"))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["coverage"]["anamnesis"] == "skipped:anahtar yok"
    assert not fed.called("anamnesis", "ingest_document")


def test_no_textbook_with_pages_falls_back_to_program_frame(tmp_path):
    fed = FakeFed(_responses(**{("maarif-mufredat", "list_textbooks"): [{"document_id": 196, "title": "x", "page_count": 0}]}))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["cerceve"]["kind"] == "program"
    assert body["cerceve"]["document_id"] == 9
    assert body["kitap_sayfalari"] == []
    assert not fed.called("maarif-mufredat", "get_document_text")


def test_no_figure_hits_means_no_page_fetch(tmp_path):
    fed = FakeFed(_responses(**{("maarif-mufredat", "search_figures"): {"query": "x", "count": 0, "figures": []}}))
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["cerceve"]["sayfalar"] is None
    assert "sayfa" in body["cerceve"]["not"]
    assert not fed.called("maarif-mufredat", "get_document_text")


def test_textbook_step_failure_degrades_mufredat_but_keeps_verified_outcomes(tmp_path):
    fed = FakeFed(_responses(), fail={("maarif-mufredat", "list_textbooks")})
    body, runs = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["status"] == "ok"
    assert body["kazanimlar"][0]["code"] == "FB.5.4.1.1"
    assert body["coverage"]["maarif-mufredat"] == "degraded:timeout"
    assert body["cerceve"]["kind"] is None and "list_textbooks" in body["cerceve"]["not"]
    assert runs.load(body["run_id"])["coverage"]["maarif-mufredat"] == "degraded:timeout"


def test_egitim_kaynak_failure_is_degraded(tmp_path):
    fed = FakeFed(_responses(), fail={("egitim-kaynak", "kb_search")})
    body, _ = _build(tmp_path, fed, konu="maddenin halleri")
    assert body["oer"] == [] and body["coverage"]["egitim-kaynak"] == "degraded:timeout"


def test_outcome_code_adds_kb_for_outcome(tmp_path):
    fed = FakeFed(_responses())
    body, _ = _build(tmp_path, fed, kazanim_kodu="FB.5.4.1.1")
    assert fed.called("egitim-kaynak", "kb_for_outcome")[0][2] == {"outcome_code": "FB.5.4.1.1", "top_k": 3}
    assert body["kazanim_eslesmesi"] == {"status": "degraded", "reason": "interim_low_relevance", "sonuc_sayisi": 0}


@pytest.mark.parametrize("sinif,status", [("13", "gecersiz_sinif"), ("abc", "gecersiz_sinif")])
def test_invalid_grade(tmp_path, sinif, status):
    runs = RunStore(tmp_path)
    body = kapsam.KapsamBuilder(FakeFed(_responses()), runs).build(FULL, "Fen Bilimleri", sinif, konu="x")
    assert body["status"] == status
    assert not (tmp_path / "edupedia_runs").exists()


def test_verification_error_passes_status_without_run(tmp_path):
    fed = FakeFed(_responses(), fail={("maarif-mufredat", "list_subjects")})
    body, _ = _build(tmp_path, fed, konu="x")
    assert body["status"] == "manual_required"
    assert body["coverage"] == {"maarif-mufredat": "degraded:timeout"}
    assert "run_id" not in body
    assert not (tmp_path / "edupedia_runs").exists()


def test_anamnesis_doc_id_stays_within_limit():
    long_id = kapsam.anamnesis_doc_id("abcdef012345", 123456789, 100000, 100005)
    assert len(long_id.encode()) <= 56
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_kapsam.py -v`
Expected: FAIL — `AttributeError: module 'src.mcp_server.kapsam' has no attribute 'KapsamBuilder'`.

- [ ] **Step 3: Append the frame builder to `src/mcp_server/kapsam.py`**

Add to the imports at the top of the file:

```python
import time
from datetime import datetime, timezone
from typing import Callable

from src.mcp_server.coverage import Coverage
from src.mcp_server.federation import ANAMNESIS, EGITIM_KAYNAK
from src.mcp_server.runs import RunStore
```

Append at the end of the file:

```python
PAGE_WINDOW = 6
FIGURE_MAX = 6
OER_MAX = 5
CAVEAT = ("Müfredat ve ders kitabı verileri maarif-mufredat korpusundan, açık kaynaklar egitim-kaynak'tan gelir; "
          "boş sonuç yokluk kanıtı değildir. MODULE_DATA'daki her olgusal iddia kitap sayfasına dayandırılmalıdır.")
NEXT_STEP = ("Derin okuma için edupedia_kaynak_oku(run_id, soru); MODULE_DATA verification.frame_source için "
             "cerceve.document_id ve sayfaları kullan; segment kurgusu için edupedia_rehber('segmentler').")


def anamnesis_doc_id(run_id: str, document_id: int, first: int, last: int) -> str:
    doc_id = f"edupedia:{run_id}:kitap/{document_id}/{first}-{last}"
    if len(doc_id.encode("utf-8")) <= 56:
        return doc_id
    return f"edupedia:{run_id}:k{document_id}"[:56]


class KapsamBuilder:
    def __init__(self, federation: Federation, runs: RunStore, clock: Callable[[], float] = time.time) -> None:
        self.federation = federation
        self.runs = runs
        self.clock = clock

    def build(self, email: str, ders: str, sinif: str | int, konu: str | None = None,
              kazanim_kodu: str | None = None) -> dict[str, Any]:
        cov = Coverage()
        grade = normalize_grade(sinif)
        if grade is None:
            return {"status": "gecersiz_sinif", "sinif": str(sinif), "mcp_verified": False}
        try:
            subject = resolve_subject(self.federation, ders)
            verified = verify_outcomes(self.federation, subject["slug"], grade, konu, kazanim_kodu)
        except KapsamError as exc:
            if exc.status == "manual_required":
                cov.degraded(MUFREDAT, exc.detay.get("neden", "hata"))
            else:
                cov.hit(MUFREDAT)
            return {"status": exc.status, **exc.detay, "coverage": cov.as_dict(), "mcp_verified": False}
        cov.hit(MUFREDAT)
        for row in verified["uyusmazlik"]:
            if row["alan"] == "sinif":
                grade = row["mufredat"]
        run_id = self.runs.new_id()
        query = konu or (verified["kazanimlar"][0]["text"][:120] if verified["kazanimlar"] else subject["name"])

        try:
            cerceve, pages, figures = self._frame(run_id, subject["slug"], grade, query, verified["kazanimlar"])
        except KapsamError as exc:
            cov.degraded(MUFREDAT, exc.detay.get("neden", "hata"))
            cerceve = {"kind": None, "document_id": None, "title": None, "sayfalar": None,
                       "not": f"Ders kitabı çerçevesi alınamadı ({exc.detay.get('arac')}); kazanımlar doğrulandı."}
            pages, figures = [], []
        self._ingest(cov, run_id, cerceve, pages)
        oer, eslesme = self._oer(cov, konu or query, kazanim_kodu)

        body: dict[str, Any] = {
            "status": "ok", "run_id": run_id, "ders": subject, "sinif": grade,
            "kazanimlar": verified["kazanimlar"], "uyusmazlik": verified["uyusmazlik"],
            "cerceve": cerceve,
            "kitap_sayfalari": [{"page_no": p["page_no"], "ozet": (p.get("text") or "")[:400]} for p in pages],
            "figur_adaylari": figures, "oer": oer,
        }
        if eslesme is not None:
            body["kazanim_eslesmesi"] = eslesme
        body.update({"coverage": cov.as_dict(), "caveat": CAVEAT, "sonraki_adim": NEXT_STEP, "mcp_verified": False})
        self.runs.save(run_id, {
            "run_id": run_id, "created_by": email,
            "created_at": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="seconds"),
            "girdi": {"ders": ders, "sinif": str(sinif), "konu": konu, "kazanim_kodu": kazanim_kodu},
            "ders": subject, "sinif": grade, "kazanimlar": verified["kazanimlar"], "cerceve": cerceve,
            "coverage": cov.as_dict(),
        })
        return body

    def _frame(self, run_id: str, slug: str, grade: str, query: str,
               kazanimlar: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        books = [b for b in _mufredat(self.federation, "list_textbooks", {"subject": slug, "grade": grade, "limit": 20}, "liste")
                 if int(b.get("page_count") or 0) > 0]
        if not books:
            doc = kazanimlar[0]["document_id"] if kazanimlar else None
            return ({"kind": "program", "document_id": doc, "title": None, "sayfalar": None,
                     "not": "Bu ders ve sınıf için tam metinli ders kitabı yok; çerçeve öğretim programıdır."}, [], [])
        book = books[0]
        doc_id = int(book["document_id"])
        found = _mufredat(self.federation, "search_figures",
                          {"query": query, "subject": slug, "grade": grade, "document_id": doc_id, "limit": 12}, "nesne")
        figs = sorted((f for f in found.get("figures") or [] if f.get("page_no")), key=lambda f: (f["page_no"], f["figure_id"]))
        figures = [{"figure_id": f["figure_id"], "page_no": f["page_no"], "etiket": f.get("label") or "",
                    "aciklama": (f.get("caption") or f.get("snippet") or "")[:200]} for f in figs[:FIGURE_MAX]]
        cerceve: dict[str, Any] = {"kind": "textbook", "document_id": doc_id, "title": book.get("title"), "sayfalar": None}
        if not figs:
            cerceve["not"] = "Figür aramasında sayfa isabeti yok; sayfa penceresi seçilmedi, kitapta konuyu elle doğrula."
            return cerceve, [], figures
        first = max(1, figs[0]["page_no"] - 1)
        last = min(int(book["page_count"]), first + PAGE_WINDOW - 1)
        text = _mufredat(self.federation, "get_document_text",
                         {"document_id": doc_id, "page_range": f"{first}-{last}", "max_chars": 60000}, "nesne")
        if text.get("error"):
            cerceve["not"] = f"Sayfa metni alınamadı: {text.get('error')}"
            return cerceve, [], figures
        pages = [p for p in text.get("pages") or [] if isinstance(p, dict)]
        for p in pages:
            self.runs.save_page(run_id, doc_id, int(p["page_no"]), p.get("text") or "")
        cerceve["sayfalar"] = f"{first}-{last}"
        return cerceve, pages, figures

    def _ingest(self, cov: Coverage, run_id: str, cerceve: dict[str, Any], pages: list[dict[str, Any]]) -> None:
        if not self.federation.configured(ANAMNESIS):
            cov.skipped(ANAMNESIS, "anahtar yok")
            return
        if not pages:
            cov.skipped(ANAMNESIS, "alınacak sayfa yok")
            return
        first, last = pages[0]["page_no"], pages[-1]["page_no"]
        text = "\n\n".join(f"=== Sayfa {p['page_no']} ===\n{p.get('text') or ''}" for p in pages)
        try:
            self.federation.call(ANAMNESIS, "ingest_document", {
                "text": text, "doc_id": anamnesis_doc_id(run_id, cerceve["document_id"], first, last),
                "collection": f"edupedia:run:{run_id}", "title": cerceve.get("title") or "ders kitabı",
                "source": "maarif-mufredat", "ttl_hours": 168,
            }, beklenen="nesne")
            cov.hit(ANAMNESIS)
        except FederationError as exc:
            cov.degraded(ANAMNESIS, exc.reason)

    def _oer(self, cov: Coverage, query: str, kazanim_kodu: str | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        if not self.federation.configured(EGITIM_KAYNAK):
            cov.skipped(EGITIM_KAYNAK, "anahtar yok")
            return [], None
        try:
            found = self.federation.call(EGITIM_KAYNAK, "kb_search", {"q": query, "top_k": OER_MAX}, beklenen="nesne")
        except FederationError as exc:
            cov.degraded(EGITIM_KAYNAK, exc.reason)
            return [], None
        oer = [{
            "doc_id": r.get("doc_id"), "baslik": r.get("title"),
            "pasaj": (r.get("passage") or "")[: 300 if r.get("quote_allowed") else 160],
            "lisans": r.get("license"), "alinti_izni": bool(r.get("quote_allowed")),
            "kaynak_url": r.get("source_url"), "eslesme": r.get("match_kind"),
        } for r in (found.get("results") or [])[:OER_MAX]]
        cov.hit(EGITIM_KAYNAK) if oer else cov.empty(EGITIM_KAYNAK)
        eslesme = None
        if kazanim_kodu:
            try:
                match = self.federation.call(EGITIM_KAYNAK, "kb_for_outcome",
                                             {"outcome_code": kazanim_kodu, "top_k": 3}, beklenen="nesne")
                eslesme = {"status": match.get("status"), "reason": match.get("reason"),
                           "sonuc_sayisi": len(match.get("results") or [])}
            except FederationError as exc:
                eslesme = {"status": "degraded", "reason": exc.reason, "sonuc_sayisi": 0}
        return oer, eslesme
```

- [ ] **Step 4: Wire `Tools.kapsam` and register the tool**

In `src/mcp_server/tools.py` add `from src.mcp_server.kapsam import KapsamBuilder` and `from src.mcp_server.runs import RunStore`; replace `Tools.__init__` with:

```python
    def __init__(self, settings: Settings, federation: Federation, clock: Callable[[], float] = time.time,
                 dashboard: DashboardContext | None = None, runs: RunStore | None = None) -> None:
        self.settings = settings
        self.federation = federation
        self.clock = clock
        self.dashboard = dashboard
        self.runs = runs if runs is not None else RunStore(settings.data_dir)
```

and add:

```python
    def kapsam(self, email: str, ders: str, sinif: str, konu: str | None = None,
               kazanim_kodu: str | None = None) -> dict[str, Any]:
        return KapsamBuilder(self.federation, self.runs, self.clock).build(email, ders, sinif, konu, kazanim_kodu)
```

In `src/mcp_server/server.py`, inside `build_server` after `edupedia_baglam`:

```python
    @mcp.tool(annotations=_RO)
    def edupedia_kapsam(ctx: Context, ders: str, sinif: str, konu: str | None = None,
                        kazanim_kodu: str | None = None) -> dict[str, Any]:
        """Ders + sınıf + (konu veya kazanım kodu) için müfredatı doğrular; ders kitabı çerçevesini, sayfa özetlerini,
        figür adaylarını ve açık kaynak özetini döner. Sınıf ve ders koddan tahmin edilmez; otorite müfredattır.
        Modül üretiminden önce ZORUNLU; dönen run_id sonraki araçlara verilir."""
        return tools.kapsam(caller_email(ctx), ders=ders, sinif=sinif, konu=konu, kazanim_kodu=kazanim_kodu)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mcp_kapsam.py tests/test_mcp_kapsam_dogrulama.py tests/test_mcp_server.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server/kapsam.py src/mcp_server/tools.py src/mcp_server/server.py tests/test_mcp_kapsam.py
git commit -m "feat(ted-mcp): edupedia_kapsam — ders kitabı çerçevesi, figür sayfa penceresi, OER ve anamnesis alımı

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 12: `edupedia_kaynak_oku`, belgeler ve ağsız tam test kapısı

**Files:**
- Create: `src/mcp_server/kaynak_oku.py`
- Modify: `src/mcp_server/tools.py` (`Tools.kaynak_oku`)
- Modify: `src/mcp_server/server.py` (register `edupedia_kaynak_oku`)
- Modify: `CLAUDE.md` (append `ted-mcp` section)
- Test: `tests/test_mcp_kaynak_oku.py`

**Interfaces:**
- Consumes: `RunStore.load(run_id)`, `RunStore.pages(run_id)`, `runs.RUN_ID_RE`, `Coverage`, `federation.ANAMNESIS`, `FederationError`.
- anamnesis contract: `hybrid_query(query, collection (required), k 1..24, per_chunk_chars 200..2000, max_edges 0..120) -> {query, collection, retrieval: {degraded, …}, chunks: [{doc_id, idx, score, title?, text, …}], graph, …}`; citation `doc_id::idx`.
- Produces:
  - `kaynak_oku.KaynakOkuyucu(federation: Federation, runs: RunStore)` with `oku(run_id: str, soru: str, top_k: int = 5) -> dict`.
  - `kaynak_oku.local_passages(pages: list[dict], soru: str, top_k: int) -> list[dict]` (BM25; `ref` = `local:<document_id>/<page_no>#<paragraf>`).
  - `Tools.kaynak_oku(email: str, run_id: str, soru: str, top_k: int = 5) -> dict`.
  - MCP tool `edupedia_kaynak_oku(ctx, run_id: str, soru: str, top_k: int = 5)`.

Yanıt: `status` (`ok` | `run_bulunamadi` | `gecersiz_sorgu`), `run_id`, `soru`, `yontem` (`anamnesis` | `yerel`), `pasajlar [{ref, sayfa, metin≤800, skor}]`, `coverage`, `caveat`, `mcp_verified: false`. `top_k` 1–8'e sıkıştırılır. Aile listesindeki her `full` hesap aynı çalıştırmayı okuyabilir (aile kataloğu modeli).

- [ ] **Step 1: Write the failing test**

`tests/test_mcp_kaynak_oku.py`:

```python
"""edupedia_kaynak_oku: scoped anamnesis query with an honest local BM25 fallback."""
import pytest

from src.mcp_server.federation import FederationError
from src.mcp_server.kaynak_oku import KaynakOkuyucu, local_passages
from src.mcp_server.runs import RunStore


class FakeFed:
    def __init__(self, response=None, configured=True, fail=False):
        self.response, self._configured, self.fail, self.calls = response, configured, fail, []

    def configured(self, server):
        return self._configured

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool, args, beklenen))
        if self.fail:
            raise FederationError(server, tool, "timeout")
        return self.response


@pytest.fixture
def runs(tmp_path):
    store = RunStore(tmp_path)
    store.save("abcdef012345", {"run_id": "abcdef012345", "created_by": "drmahirkurt@gmail.com"})
    store.save_page("abcdef012345", 197, 112, "Katı maddelerin tanecikleri düzenlidir.\n\nSıvılar akışkandır.")
    store.save_page("abcdef012345", 197, 113, "Buharlaşma sıvının gaza dönüşmesidir.\n\nYoğuşma tersidir.")
    return store


CHUNKS = {"query": "q", "collection": "edupedia:run:abcdef012345", "retrieval": {"degraded": False},
          "chunks": [{"doc_id": "edupedia:abcdef012345:kitap/197/112-113", "idx": 2, "score": 0.91,
                      "text": "Buharlaşma sıvının gaza dönüşmesidir." + " x" * 600}]}


def test_anamnesis_query_is_collection_scoped(runs):
    fed = FakeFed(CHUNKS)
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma nedir", top_k=20)
    server, tool, args, beklenen = fed.calls[0]
    assert (server, tool, beklenen) == ("anamnesis", "hybrid_query", "nesne")
    assert args == {"query": "buharlaşma nedir", "collection": "edupedia:run:abcdef012345", "k": 8,
                    "per_chunk_chars": 800, "max_edges": 0}
    assert body["status"] == "ok" and body["yontem"] == "anamnesis"
    assert body["pasajlar"][0]["ref"] == "edupedia:abcdef012345:kitap/197/112-113::2"
    assert len(body["pasajlar"][0]["metin"]) <= 800
    assert body["coverage"] == {"anamnesis": "hit"}
    assert body["mcp_verified"] is False


@pytest.mark.parametrize("fed,state", [
    (FakeFed(fail=True), "degraded:timeout"),
    (FakeFed(configured=False), "skipped:anahtar yok"),
    (FakeFed({"chunks": [], "retrieval": {"degraded": False}}), "empty"),
])
def test_falls_back_to_local_pages(runs, fed, state):
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    assert body["yontem"] == "yerel"
    assert body["coverage"]["anamnesis"] == state
    assert body["pasajlar"][0]["sayfa"] == 113
    assert body["pasajlar"][0]["ref"] == "local:197/113#0"


def test_degraded_anamnesis_retrieval_is_reported_but_used(runs):
    fed = FakeFed({**CHUNKS, "retrieval": {"degraded": True}})
    body = KaynakOkuyucu(fed, runs).oku("abcdef012345", "buharlaşma")
    assert body["yontem"] == "anamnesis"
    assert body["coverage"]["anamnesis"] == "degraded:anamnesis_degraded"


def test_unknown_run_and_empty_question(runs):
    reader = KaynakOkuyucu(FakeFed(CHUNKS), runs)
    assert reader.oku("ffffffffffff", "x")["status"] == "run_bulunamadi"
    assert reader.oku("../../etc", "x")["status"] == "run_bulunamadi"
    assert reader.oku("abcdef012345", "  ")["status"] == "gecersiz_sorgu"


def test_local_passages_rank_by_term_and_fold_turkish_case():
    pages = [{"document_id": 1, "page_no": 5, "text": "Işık kırılır.\n\nSes yayılır."},
             {"document_id": 1, "page_no": 6, "text": "IŞIK hızlıdır ve ışık düz gider."}]
    hits = local_passages(pages, "ışık", top_k=2)
    assert [h["sayfa"] for h in hits] == [6, 5]
    assert local_passages(pages, "uzay", top_k=2) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mcp_kaynak_oku.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.mcp_server.kaynak_oku'`.

- [ ] **Step 3: Create `src/mcp_server/kaynak_oku.py`**

```python
"""edupedia_kaynak_oku: bounded reading inside one run's sources (anamnesis first, local BM25 fallback)."""
from __future__ import annotations

import math
import re
from typing import Any

from src.mcp_server.coverage import Coverage
from src.mcp_server.federation import ANAMNESIS, Federation, FederationError
from src.mcp_server.runs import RUN_ID_RE, RunStore

PASSAGE_MAX = 800
CAVEAT = "Pasajlar yalnız bu çalıştırmada alınan kaynaklardan gelir; boş sonuç yokluk kanıtı değildir."


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def _terms(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", _fold(text)) if len(t) >= 3]


def local_passages(pages: list[dict[str, Any]], soru: str, top_k: int) -> list[dict[str, Any]]:
    query = set(_terms(soru))
    if not query:
        return []
    docs = []
    for page in pages:
        for i, para in enumerate(p for p in re.split(r"\n\s*\n", page.get("text") or "") if p.strip()):
            docs.append((page, i, para, _terms(para)))
    if not docs:
        return []
    avg = sum(len(d[3]) for d in docs) / len(docs) or 1.0
    df = {t: sum(1 for d in docs if t in d[3]) for t in query}
    k1, b = 1.2, 0.75
    scored = []
    for page, i, para, terms in docs:
        score = 0.0
        for t in query:
            tf = terms.count(t)
            if not tf:
                continue
            idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(terms) / avg))
        if score > 0:
            scored.append((score, page, i, para))
    scored.sort(key=lambda row: -row[0])
    return [{"ref": f"local:{p['document_id']}/{p['page_no']}#{i}", "sayfa": p["page_no"],
             "metin": para.strip()[:PASSAGE_MAX], "skor": round(s, 4)} for s, p, i, para in scored[:top_k]]


class KaynakOkuyucu:
    def __init__(self, federation: Federation, runs: RunStore) -> None:
        self.federation = federation
        self.runs = runs

    def oku(self, run_id: str, soru: str, top_k: int = 5) -> dict[str, Any]:
        base: dict[str, Any] = {"run_id": run_id, "soru": soru, "caveat": CAVEAT, "mcp_verified": False}
        if not RUN_ID_RE.match(run_id or "") or self.runs.load(run_id) is None:
            return {**base, "status": "run_bulunamadi"}
        if not (soru or "").strip():
            return {**base, "status": "gecersiz_sorgu"}
        top_k = max(1, min(int(top_k), 8))
        cov = Coverage()
        if self.federation.configured(ANAMNESIS):
            try:
                found = self.federation.call(ANAMNESIS, "hybrid_query", {
                    "query": soru, "collection": f"edupedia:run:{run_id}", "k": top_k,
                    "per_chunk_chars": PASSAGE_MAX, "max_edges": 0,
                }, beklenen="nesne")
                chunks = found.get("chunks") or []
                if chunks:
                    degraded = bool((found.get("retrieval") or {}).get("degraded"))
                    cov.degraded(ANAMNESIS, "anamnesis_degraded") if degraded else cov.hit(ANAMNESIS)
                    pasajlar = [{"ref": f"{c.get('doc_id')}::{c.get('idx')}", "sayfa": None,
                                 "metin": (c.get("text") or "")[:PASSAGE_MAX], "skor": c.get("score")}
                                for c in chunks[:top_k]]
                    return {**base, "status": "ok", "yontem": "anamnesis", "pasajlar": pasajlar, "coverage": cov.as_dict()}
                cov.empty(ANAMNESIS)
            except FederationError as exc:
                cov.degraded(ANAMNESIS, exc.reason)
        else:
            cov.skipped(ANAMNESIS, "anahtar yok")
        pasajlar = local_passages(self.runs.pages(run_id), soru, top_k)
        return {**base, "status": "ok", "yontem": "yerel", "pasajlar": pasajlar, "coverage": cov.as_dict()}
```

- [ ] **Step 4: Wire the tool**

In `src/mcp_server/tools.py` add `from src.mcp_server.kaynak_oku import KaynakOkuyucu` and:

```python
    def kaynak_oku(self, email: str, run_id: str, soru: str, top_k: int = 5) -> dict[str, Any]:
        return KaynakOkuyucu(self.federation, self.runs).oku(run_id, soru, top_k=top_k)
```

In `src/mcp_server/server.py`, inside `build_server` after `edupedia_kapsam`:

```python
    @mcp.tool(annotations=_RO)
    def edupedia_kaynak_oku(ctx: Context, run_id: str, soru: str, top_k: int = 5) -> dict[str, Any]:
        """edupedia_kapsam'ın aldığı ders kitabı sayfalarında soruya en yakın pasajları döner (en fazla 8).
        Atıf için pasajın ref alanını kullan; boş sonuç yokluk kanıtı değildir."""
        return tools.kaynak_oku(caller_email(ctx), run_id=run_id, soru=soru, top_k=top_k)
```

Add to `tests/test_mcp_server.py` (reuses that file's helpers):

```python
def test_all_five_core_tools_are_listed(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    with _client(tmp_path, store) as c:
        listed = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                                  headers={**MCP_HEADERS, "authorization": f"Bearer {key}"}))
    names = {t["name"] for t in listed["result"]["tools"]}
    assert names == {"edupedia_durum", "edupedia_rehber", "edupedia_baglam", "edupedia_kapsam", "edupedia_kaynak_oku"}
```

- [ ] **Step 5: Document ted-mcp in `CLAUDE.md`**

Append this section to the end of `CLAUDE.md`:

````markdown
## ted-mcp — edupedia orkestratörü (alt proje 2)

Spec: `docs/superpowers/specs/2026-09-13-edupedia-tedy-orkestrator-design.md`. Ayrı bir ASGI süreci
(`src/mcp_server/`); Flask dashboard'u import etmez. Roller tek kaynak `src/roles.py`.

```bash
# Yerel çalıştırma (canlı birim ve tünel alt proje 3'te)
TED_MCP_FORM_SECRET=$(python3 -c 'import secrets;print(secrets.token_hex(32))') \
  .venv/bin/python -m src.mcp_server.http_app          # 127.0.0.1:8087

.venv/bin/python -m src.mcp_server.keys olustur --etiket <etiket> --email <full-rol-eposta>   # tdyM_ anahtarı
.venv/bin/python -m src.mcp_server.vendor_sync --check  # vendored edupedia varlıkları kaynağıyla eşit mi
unshare -rn .venv/bin/python -m pytest -q               # tüm testler ağsız
```

- Araçlar: `edupedia_durum`, `edupedia_rehber`, `edupedia_baglam`, `edupedia_kapsam`, `edupedia_kaynak_oku`.
- Ortam: `TED_MCP_FORM_SECRET` (zorunlu, ≥32 bayt), `TED_MCP_PUBLIC_BASE_URL` (varsayılan `https://mcp.tedy.online`),
  `TED_MCP_ALLOWED_HOSTS`, `TED_MCP_HOST`/`TED_MCP_PORT`, `TED_DASHBOARD_API_URL` (varsayılan `http://127.0.0.1:8085`),
  `TED_DASHBOARD_API_KEY` (`ted-mcp` etiketli `tdyK_` anahtar), `MUFREDAT_MCP_API_KEY`, `EGITIM_KAYNAK_MCP_API_KEY`,
  `ANAMNESIS_MCP_API_KEY`.
- OAuth onayı Google girişiyle; yalnız `full` rol. Token deposu `output/ted_mcp_oauth.sqlite3` (yalnız hash).
- Vendored dosyaları (`src/mcp_server/vendor/`) elle düzenleme; `vendor_sync` ile güncelle, `PROVENANCE.json` testle sabitli.
- Tuzak: `.venv/bin/pip` shebang'i eski yola işaret eder → `.venv/bin/python -m pip` kullan.
````

- [ ] **Step 6: Run the full offline gate**

Run: `.venv/bin/python -m pytest tests/test_mcp_kaynak_oku.py tests/test_mcp_server.py -v`
Expected: all PASS.

Run: `unshare -rn .venv/bin/python -m pytest -q; echo "rc=$?"`
Expected: every test passes (the pre-existing TED suite plus all `tests/test_roles.py` and `tests/test_mcp_*.py`), `rc=0`. Paste the final summary line into the task report.

Run: `.venv/bin/python -m src.mcp_server.vendor_sync --check; echo "rc=$?"`
Expected: `rc=0`.

Run: `TED_MCP_FORM_SECRET=$(python3 -c 'import secrets;print(secrets.token_hex(32))') .venv/bin/python -c "from src.env_loader import load_env; load_env(); from src.mcp_server.http_app import create_app_from_env; print(type(create_app_from_env()).__name__)"`
Expected: `Starlette`

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server/kaynak_oku.py src/mcp_server/tools.py src/mcp_server/server.py tests/test_mcp_kaynak_oku.py tests/test_mcp_server.py CLAUDE.md
git commit -m "feat(ted-mcp): edupedia_kaynak_oku (anamnesis + yerel BM25), CLAUDE.md bölümü, ağsız tam test kapısı

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Plan sonu — alt proje 2 kabul ölçütleri

1. `unshare -rn .venv/bin/python -m pytest -q` sıfır hatayla geçer.
2. `tools/list` tam olarak beş aracı döner; `serverInfo.version == "0.1.0"`.
3. OAuth uçtan uca testi (onay → kod → token → yenileme → araç çağrısı kimlikle) geçer; `reader` rol 403 alır.
4. Vendored varlıklar `PROVENANCE.json` ile eşit ve kaynakla sapmasız (`vendor_sync --check` rc 0).
5. Canlı dağıtım, tünel, Google OAuth origin, `.env` hazırlığı ve gerçek token'la `initialize` + `tools/list` ölçümü **alt proje 3**'tür; bu planın kapsamı dışındadır.
