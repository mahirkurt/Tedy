# Public API Key Authentication

**Date:** 2026-03-15
**Status:** Approved

## Goal

Enable third-party applications (mobile apps, automation tools, other web apps) to access all existing `/api/*` endpoints using API key authentication, without changing the dashboard's Google Sign-In flow.

## Design

### Auth Flow Change

The existing `require_auth` decorator in `src/dashboard_api.py` is extended to accept API keys alongside session auth. Check order:

1. `TEST_AUTH_BYPASS` env var → pass (existing test mode)
2. `session["user_email"]` exists → pass (existing dashboard auth)
3. `Authorization: Bearer <key>` header → validate key, pass
4. `?api_key=<key>` query parameter → validate key, pass
5. None of the above → 401 Unauthorized

API key validation: iterate over stored keys using `hmac.compare_digest()` for timing-safe comparison. With a small number of keys this is effectively instant.

Keys without the `tdyK_` prefix are rejected immediately before comparison (short-circuit for obviously invalid tokens like OAuth JWTs accidentally sent in the Bearer header).

When a request authenticates via API key, log at INFO level: `"API key auth: <first 8 chars>... -> <method> <path>"`.

### Key Storage

- Keys are stored in `.env` as a comma-separated list: `API_KEYS=label1:key1,label2:key2` (label is optional, for identifying which client uses which key)
- Loaded once at module level into a list of `(label, key)` tuples
- If `API_KEYS` is unset or empty, API key auth is disabled — only session auth works

### Key Generation

A CLI mode is added to `dashboard_api.py`:

```bash
python src/dashboard_api.py --generate-key
# Output: tdyK_<random 32 bytes urlsafe base64>
```

The `tdyK_` prefix makes keys identifiable in logs and config. The generated key is printed to stdout — the user manually adds it to `.env`.

### Usage Examples

```bash
# Via Authorization header (preferred for production)
curl -H "Authorization: Bearer tdyK_a8f3..." https://tedy.online/api/schedule

# Via query parameter (local testing only — see security note)
curl "https://tedy.online/api/homework?api_key=tdyK_..."
```

> **Security note:** Query parameters are logged by web servers, reverse proxies (Cloudflare), and browser history. Use the `Authorization` header for production integrations. The query parameter option exists for quick local/debugging use only.

### Write Endpoint Access

API key holders get full access to all endpoints, including write/mutation endpoints (`POST /api/homework/mark-done`, `/api/homework/photo`, `/api/assistant/chat`, `/api/assistant/reindex`, `/api/private-lessons`). This is intentional — the API is designed for trusted first-party integrations. Per-key permission scoping may be added later if needed.

### Files Changed

| File | Change |
|------|--------|
| `src/dashboard_api.py` | Extend `require_auth` with API key check; add `API_KEYS` loading at module level; add `--generate-key` CLI flag; INFO logging for API key auth |
| `.env` | Add `API_KEYS=` entry |
| `tests/test_dashboard_api.py` | Add tests for API key auth (header, query param, invalid key, missing key, empty API_KEYS) |
| `CLAUDE.md` | Document `API_KEYS` env var and `--generate-key` command |

### Out of Scope

- Rate limiting — not needed given small user base
- Per-key permissions (read-only vs read-write) — all endpoints have equal access (see Write Endpoint Access above)
- Key revocation UI — remove from `.env` and restart service
- Separate `/v2/` or `/public/` prefix — reuses existing `/api/*` routes
