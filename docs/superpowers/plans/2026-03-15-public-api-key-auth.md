# Public API Key Authentication — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable third-party apps to access all `/api/*` endpoints via API key (`Authorization: Bearer` header or `?api_key=` query param), without changing the dashboard's Google Sign-In flow.

**Architecture:** Extend the existing `require_auth` decorator in `dashboard_api.py` to check for API keys after session auth. Keys stored in `.env` as `API_KEYS=label:key,...`. Timing-safe comparison via `hmac.compare_digest()`.

**Tech Stack:** Python, Flask, hmac, secrets

**Spec:** `docs/superpowers/specs/2026-03-15-public-api-key-auth-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/dashboard_api.py` | Modify (lines 1-10 imports, lines 28-55 config, lines 90-100 auth) | API key loading, validation, `require_auth` extension, `--generate-key` CLI |
| `tests/test_dashboard_api.py` | Modify (add new test class) | API key auth tests |
| `CLAUDE.md` | Modify | Document `API_KEYS` env var and `--generate-key` command |
| `.env` | Modify | Add `API_KEYS=` entry |

---

## Chunk 1: Implementation

### Task 1: Add API key loading and validation helper

**Files:**
- Modify: `src/dashboard_api.py:1-10` (imports)
- Modify: `src/dashboard_api.py:28-55` (config section)

- [ ] **Step 1: Add `hmac` import**

In `src/dashboard_api.py`, add `import hmac` to the imports block (after `import secrets`).

- [ ] **Step 2: Add API key loading at module level**

After the `ASSISTANT_ADMIN_EMAILS` block (~line 58), add:

```python
def _load_api_keys() -> list[tuple[str, str]]:
    """Load API keys from env. Format: 'label:key,label2:key2' or 'key1,key2'."""
    raw = os.environ.get("API_KEYS", "").strip()
    if not raw:
        return []
    keys = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            label, key = entry.split(":", 1)
            keys.append((label.strip(), key.strip()))
        else:
            keys.append(("default", entry))
    return keys

API_KEYS = _load_api_keys()
```

- [ ] **Step 3: Add API key validation helper**

```python
def _validate_api_key(provided: str) -> str | None:
    """Return label if key is valid, None otherwise. Timing-safe."""
    if not provided or not provided.startswith("tdyK_"):
        return None
    for label, stored_key in API_KEYS:
        if hmac.compare_digest(provided, stored_key):
            return label
    return None
```

- [ ] **Step 4: Commit**

```bash
git add src/dashboard_api.py
git commit -m "feat: add API key loading and validation helper"
```

### Task 2: Extend `require_auth` decorator

**Files:**
- Modify: `src/dashboard_api.py:90-100`

- [ ] **Step 1: Write failing test for API key auth via header**

In `tests/test_dashboard_api.py`, add a new test class:

```python
class TestApiKeyAuth:
    """Tests for API key authentication (header and query param)."""

    @pytest.fixture(autouse=True)
    def _disable_test_bypass(self, monkeypatch):
        """Disable TEST_AUTH_BYPASS so we can test real auth paths."""
        monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)

    @pytest.fixture
    def valid_key(self, monkeypatch):
        key = "tdyK_test-valid-key-for-unit-tests"
        monkeypatch.setattr(dashboard_api, "API_KEYS", [("test", key)])
        return key

    def test_bearer_header_grants_access(self, client, valid_key):
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": f"Bearer {valid_key}"},
        )
        assert resp.status_code == 200

    def test_query_param_grants_access(self, client, valid_key):
        resp = client.get(f"/api/schedule?api_key={valid_key}")
        assert resp.status_code == 200

    def test_invalid_key_returns_401(self, client, valid_key):
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": "Bearer tdyK_wrong-key"},
        )
        assert resp.status_code == 401

    def test_no_auth_returns_401(self, client):
        monkeypatch_obj = pytest.MonkeyPatch()
        monkeypatch_obj.setattr(dashboard_api, "API_KEYS", [])
        try:
            resp = client.get("/api/schedule")
            assert resp.status_code == 401
        finally:
            monkeypatch_obj.undo()

    def test_non_tdyk_prefix_rejected(self, client, valid_key):
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": "Bearer not-a-valid-prefix-key"},
        )
        assert resp.status_code == 401

    def test_empty_api_keys_disables_key_auth(self, client, monkeypatch):
        monkeypatch.setattr(dashboard_api, "API_KEYS", [])
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": "Bearer tdyK_anything"},
        )
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `TEST_AUTH_BYPASS=1 pytest tests/test_dashboard_api.py::TestApiKeyAuth -v`
Expected: FAIL — `require_auth` doesn't check API keys yet.

- [ ] **Step 3: Extend `require_auth` to accept API keys**

Replace the `require_auth` function at `src/dashboard_api.py:92-100`:

```python
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if TEST_AUTH_BYPASS:
            return f(*args, **kwargs)
        if session.get("user_email"):
            return f(*args, **kwargs)
        # API key: Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            key = auth_header[7:]
            label = _validate_api_key(key)
            if label is not None:
                app.logger.info("API key auth: %s... -> %s %s", key[:8], request.method, request.path)
                return f(*args, **kwargs)
        # API key: query parameter
        query_key = request.args.get("api_key", "")
        if query_key:
            label = _validate_api_key(query_key)
            if label is not None:
                app.logger.info("API key auth: %s... -> %s %s", query_key[:8], request.method, request.path)
                return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401
    return decorated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `TEST_AUTH_BYPASS=1 pytest tests/test_dashboard_api.py::TestApiKeyAuth -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `TEST_AUTH_BYPASS=1 pytest tests/test_dashboard_api.py -v`
Expected: All tests PASS (existing + new).

- [ ] **Step 6: Commit**

```bash
git add src/dashboard_api.py tests/test_dashboard_api.py
git commit -m "feat: extend require_auth to accept API keys via header and query param"
```

### Task 3: Add `--generate-key` CLI

**Files:**
- Modify: `src/dashboard_api.py` (bottom of file, before `if __name__`)

- [ ] **Step 1: Add CLI key generation**

At the bottom of `dashboard_api.py`, modify the `if __name__ == "__main__"` block:

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TED Dashboard API")
    parser.add_argument("--generate-key", action="store_true", help="Generate a new API key")
    args = parser.parse_args()
    if args.generate_key:
        key = f"tdyK_{secrets.token_urlsafe(32)}"
        print(f"\nNew API key: {key}\n")
        print("Add to .env:  API_KEYS=myapp:" + key)
        print("Or append:    API_KEYS=...existing...,myapp:" + key)
    else:
        app.run(host="0.0.0.0", port=8085, debug=True)
```

- [ ] **Step 2: Test CLI**

Run: `python src/dashboard_api.py --generate-key`
Expected: Prints a key starting with `tdyK_` and usage instructions.

- [ ] **Step 3: Commit**

```bash
git add src/dashboard_api.py
git commit -m "feat: add --generate-key CLI for API key generation"
```

### Task 4: Update CLAUDE.md and .env

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.env`

- [ ] **Step 1: Add API key docs to CLAUDE.md**

In the `## Required Credentials` section, add after the `.env` bullet:

```markdown
- `API_KEYS` — Comma-separated API keys in `.env` for third-party access (`API_KEYS=label:tdyK_...`). Generate with `python src/dashboard_api.py --generate-key`
```

In the `## Commands` section under `# Dashboard`, add:

```markdown
python src/dashboard_api.py --generate-key  # Generate a new API key for third-party access
```

- [ ] **Step 2: Generate and add a key to `.env`**

Run: `python src/dashboard_api.py --generate-key`

Copy the output key and add to `.env`:

```
API_KEYS=default:<generated-key>
```

- [ ] **Step 3: Commit CLAUDE.md only (`.env` is gitignored)**

```bash
git add CLAUDE.md
git commit -m "docs: document API key auth and --generate-key command"
```

### Task 5: End-to-end verification

- [ ] **Step 1: Restart dashboard service**

```bash
systemctl --user restart ted-dashboard
```

- [ ] **Step 2: Test with curl against live service**

```bash
curl -s -H "Authorization: Bearer <your-key>" http://localhost:8085/api/health | python -m json.tool
curl -s -H "Authorization: Bearer <your-key>" http://localhost:8085/api/schedule | python -m json.tool
```

Expected: JSON responses with data (not 401).

- [ ] **Step 3: Test invalid key is rejected**

```bash
curl -s -H "Authorization: Bearer tdyK_invalid" http://localhost:8085/api/schedule
```

Expected: `{"error": "Unauthorized"}` with 401 status.
