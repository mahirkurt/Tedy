"""edge_ratelimit: one per-IP block rule for ted-mcp's paths, merged into a Free plan's single rule when present."""
import io
import json

import pytest

from src.mcp_server import edge_ratelimit as edge
from src.mcp_server.tunnel_route import RouteError

ENTRY = "/zones/zone-tedy/rulesets/phases/http_ratelimit/entrypoint"
EXISTING = {"id": "r1", "version": "3", "last_updated": "2026-01-01T00:00:00Z", "action": "block",
            "expression": '(http.request.uri.path eq "/api/auth/login")', "description": "login", "enabled": True,
            "ratelimit": {"characteristics": ["ip.src", "cf.colo.id"], "period": 10, "requests_per_period": 50,
                          "mitigation_timeout": 10}}


class FakeApi:
    def __init__(self, plan="free", rules=None):
        self.plan, self.rules, self.puts = plan, rules, []

    def zone(self, name):
        return "zone-tedy", "acct-1"

    def call(self, method, path, params=None, body=None, missing_ok=False):
        if (method, path) == ("GET", "/zones/zone-tedy"):
            return {"plan": {"legacy_id": self.plan}}
        if (method, path) == ("GET", ENTRY):
            if self.rules is None:
                assert missing_ok
                return None
            return {"id": "rs1", "rules": json.loads(json.dumps(self.rules))}
        if (method, path) == ("PUT", ENTRY):
            self.puts.append(body["rules"])
            self.rules = [{**r, "id": r.get("id", f"new{i}"), "version": "1"} for i, r in enumerate(body["rules"])]
            return {"id": "rs1", "rules": self.rules}
        raise AssertionError((method, path))


class FakeApiDriftsBeforePut(FakeApi):
    """P5-1: the GET *after* the snapshot (but before PUT) returns a different ruleset than the GET
    that seeded `rules`/`new` at the top of main() — simulating another operator's concurrent edit.
    The first GET (top of main()) and the "dogrula"-style GETs after a completed run still return
    self.rules unchanged; only the second-and-later GET to the entrypoint is swapped out."""

    def __init__(self, plan="free", rules=None, drifted=None):
        super().__init__(plan, rules)
        self._entry_gets = 0
        self._drifted = drifted if drifted is not None else [EXISTING]

    def call(self, method, path, params=None, body=None, missing_ok=False):
        if (method, path) == ("GET", ENTRY):
            self._entry_gets += 1
            if self._entry_gets > 1:
                return {"id": "rs1", "rules": json.loads(json.dumps(self._drifted))}
        return super().call(method, path, params, body, missing_ok)


class FakeApiPutReadbackMismatches(FakeApi):
    """The PUT is accepted, but the ruleset read back afterwards does not match what was written —
    e.g. Cloudflare silently coerced or dropped something. main() must refuse to call this UYGULANDI."""

    def call(self, method, path, params=None, body=None, missing_ok=False):
        if (method, path) == ("PUT", ENTRY):
            self.puts.append(body["rules"])
            self.rules = [dict(EXISTING)]
            return {"id": "rs1", "rules": self.rules}
        return super().call(method, path, params, body, missing_ok)


def _run(api, *argv, clock=lambda: 1789430400.0):
    out = io.StringIO()
    rc = edge.main(["--bolge", "tedy.online", *argv], api=api, out=out, clock=clock)
    return rc, out.getvalue()


def test_expression_covers_exactly_the_public_oauth_and_mcp_paths():
    assert edge.our_expression() == (
        '(http.request.uri.path in {"/oauth/register" "/oauth/authorize" "/oauth/token" "/mcp" "/mcp/"})')
    assert edge.our_expression("mcp.tedy.online").startswith('(http.host eq "mcp.tedy.online" and ')


def test_empty_phase_creates_one_block_rule():
    rules, mode = edge.add_limit([], "free", 60)
    assert mode == "oluştur" and rules == [edge.new_rule(60)]
    assert rules[0]["action"] == "block" and rules[0]["ref"] == edge.REF
    assert rules[0]["ratelimit"] == {"characteristics": ["ip.src", "cf.colo.id"], "period": 10,
                                     "requests_per_period": 60, "mitigation_timeout": 10}


def test_free_plan_single_rule_is_merged_and_unmerge_restores_it():
    rules, mode = edge.add_limit([EXISTING], "free", 60)
    assert mode == "birleştir" and len(rules) == 1
    assert rules[0]["expression"] == f"({EXISTING['expression']}) or {edge.our_expression()}"
    assert rules[0]["id"] == "r1" and "version" not in rules[0] and rules[0]["ratelimit"] == EXISTING["ratelimit"]
    assert edge.find_ours(rules) == (0, "birleşik")
    assert edge.remove_limit(rules) == [edge.writable(EXISTING)]


@pytest.mark.parametrize("change", [
    {"action": "managed_challenge"},
    {"enabled": False},
    {"ratelimit": {**EXISTING["ratelimit"], "requests_per_period": 20}},
])
def test_merge_refuses_rules_that_would_break_mcp_clients(change):
    with pytest.raises(RouteError):
        edge.add_limit([{**EXISTING, **change}], "free", 60)


def test_existing_limit_or_undecidable_rule_sets_are_refused():
    with pytest.raises(RouteError):
        edge.add_limit([edge.new_rule(60)], "free", 60)
    with pytest.raises(RouteError):
        edge.add_limit([EXISTING, {**EXISTING, "id": "r2"}], "pro", 60)
    with pytest.raises(RouteError):
        edge.add_limit([EXISTING], "pro", 60)


def test_dry_run_prints_the_plan_and_writes_nothing():
    api = FakeApi()
    rc, out = _run(api, "ekle", "--beklenen-kural", "0")
    assert rc == 0
    assert "bölge: tedy.online (zone-tedy), plan: free" in out
    assert "http_ratelimit kuralı: 0" in out and "işlem: oluştur" in out
    assert f"  sonra: ted-mcp-hiz-siniri: block 60/10s, zaman aşımı 10s, açık=True, ifade={edge.our_expression()}" in out
    assert out.rstrip().endswith("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı")
    assert api.puts == []


def test_apply_snapshots_writes_rereads_and_verifies(tmp_path):
    api = FakeApi()
    rc, out = _run(api, "ekle", "--beklenen-kural", "0", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 0 and out.rstrip().endswith("UYGULANDI")
    assert api.puts == [[edge.new_rule(60)]]
    snapshot = next(tmp_path.glob("tedy.online-ratelimit-*.json"))
    assert snapshot.stat().st_mode & 0o777 == 0o600
    assert json.loads(snapshot.read_text()) == {"zone": "tedy.online", "rules": []}
    rc, out = _run(api, "dogrula")
    assert rc == 0 and "ted-mcp kuralı: ayrı" in out and out.rstrip().endswith("DOĞRULANDI")


def test_count_drift_is_refused_and_merge_then_remove_round_trips(tmp_path):
    api = FakeApi(rules=[EXISTING])
    assert _run(api, "ekle", "--beklenen-kural", "0", "--uygula", "--yedek-dizini", str(tmp_path / "a"))[0] == 2
    assert api.puts == []
    assert _run(api, "ekle", "--beklenen-kural", "1", "--uygula", "--yedek-dizini", str(tmp_path / "b"))[0] == 0
    assert _run(api, "dogrula")[0] == 0
    assert _run(api, "kaldir", "--beklenen-kural", "1", "--uygula", "--yedek-dizini", str(tmp_path / "c"))[0] == 0
    assert [edge.essence(r) for r in api.rules] == [edge.essence(EXISTING)]
    assert _run(api, "dogrula")[0] == 1


# --- P5-1 / P5-2: every RouteError path reachable through main() gets its own reaching test. ---


def test_uygula_without_yedek_dizini_is_refused():
    """main()'s own '--uygula için --yedek-dizini zorunlu' check, reached with a change that would
    otherwise succeed (0 existing rules matches --beklenen-kural 0) so no earlier check masks it."""
    api = FakeApi()
    rc, out = _run(api, "ekle", "--beklenen-kural", "0", "--uygula")
    assert rc == 2
    assert api.puts == []


def test_main_ekle_reports_merge_refusal_as_rc2():
    """add_limit()'s 'eylem ... elle karar' refusal, exercised through the CLI (not just directly)."""
    api = FakeApi(rules=[{**EXISTING, "action": "managed_challenge"}])
    rc, out = _run(api, "ekle", "--beklenen-kural", "1")
    assert rc == 2
    assert api.puts == []


def test_main_ekle_reports_existing_limit_as_rc2():
    """add_limit()'s 'ted-mcp hız sınırı zaten var' refusal, exercised through the CLI."""
    api = FakeApi(rules=[edge.new_rule(60)])
    rc, out = _run(api, "ekle", "--beklenen-kural", "1")
    assert rc == 2
    assert api.puts == []


def test_main_ekle_reports_undecidable_ruleset_as_rc2():
    """add_limit()'s 'otomatik karar yok' refusal (paid plan, single existing rule), through the CLI."""
    api = FakeApi(plan="pro", rules=[EXISTING])
    rc, out = _run(api, "ekle", "--beklenen-kural", "1")
    assert rc == 2
    assert api.puts == []


def test_ruleset_changed_before_put_aborts_and_writes_nothing(tmp_path):
    """P5-1: the http_ratelimit phase is re-read immediately before PUT; if it no longer matches
    what the change was computed from, main() aborts with rc 2, calls PUT zero times, and the
    snapshot backup (already written) stays on disk."""
    api = FakeApiDriftsBeforePut(rules=[])
    rc, out = _run(api, "ekle", "--beklenen-kural", "0", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 2
    assert api.puts == []
    backups = list(tmp_path.glob("tedy.online-ratelimit-*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text()) == {"zone": "tedy.online", "rules": []}


def test_put_readback_mismatch_is_refused(tmp_path):
    """The existing post-PUT re-read check: PUT succeeds but the readback disagrees with what was
    sent, so main() must not report UYGULANDI."""
    api = FakeApiPutReadbackMismatches(rules=[])
    rc, out = _run(api, "ekle", "--beklenen-kural", "0", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 2
    assert api.puts == [[edge.new_rule(60)]]
    assert "UYGULANDI" not in out
