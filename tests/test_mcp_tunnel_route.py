"""tunnel_route: merge-only ingress edits with a one-rule interlock, DNS never clobbered, token never printed."""
import io
import json

import pytest

from src.mcp_server import tunnel_route as tr

HOST, SERVICE = "mcp.tedy.online", "http://127.0.0.1:8090"
TUNNEL = "0123abcd-0000-4000-8000-000000000000"
TARGET = f"{TUNNEL}.cfargotunnel.com"
CATCH_ALL = {"service": "http_status:404"}
ARGS = ["--bolge", "tedy.online", "--tunel", "hp-ai-node", "--host", HOST]


def _ingress(n_hostnames=51):
    rules = [{"hostname": "tedy.online", "service": "http://localhost:8085", "originRequest": {}}]
    rules += [{"hostname": f"h{i}.example.com", "service": f"http://localhost:{9000 + i}"} for i in range(n_hostnames - 1)]
    return rules + [CATCH_ALL]


class FakeApi:
    def __init__(self, ingress, records=()):
        self.config = {"ingress": [dict(r) for r in ingress], "warp-routing": {"enabled": False}}
        self.records = [dict(r) for r in records]
        self.calls = []

    def zone(self, name):
        self.calls.append(("zone", name))
        return "zone-tedy", "acct-1"

    def tunnel_id(self, account_id, name):
        self.calls.append(("tunnel_id", account_id, name))
        return TUNNEL

    def tunnel_config(self, account_id, tunnel_id):
        self.calls.append(("tunnel_config",))
        return json.loads(json.dumps(self.config))

    def put_tunnel_config(self, account_id, tunnel_id, config):
        self.calls.append(("put_tunnel_config",))
        self.config = json.loads(json.dumps(config))

    def dns_records(self, zone_id, name):
        self.calls.append(("dns_records", zone_id, name))
        return [dict(r) for r in self.records]

    def create_cname(self, zone_id, name, target):
        self.calls.append(("create_cname", zone_id, name, target))
        self.records.append({"id": "rec-1", "type": "CNAME", "name": name, "content": target, "proxied": True})

    def delete_dns_record(self, zone_id, record_id):
        self.calls.append(("delete_dns_record", zone_id, record_id))
        self.records = [r for r in self.records if r["id"] != record_id]

    def writes(self):
        return [c[0] for c in self.calls if c[0] in ("put_tunnel_config", "create_cname", "delete_dns_record")]


def _run(api, *argv, clock=lambda: 1789430400.0):
    out = io.StringIO()
    rc = tr.main([*ARGS, *argv], api=api, out=out, clock=clock)
    return rc, out.getvalue()


def test_add_rule_inserts_before_catch_all_and_keeps_every_other_rule():
    old = _ingress()
    new = tr.add_rule(old, HOST, SERVICE)
    assert len(new) == 53
    assert new[:51] == old[:51] and new[-1] == CATCH_ALL
    assert new[51] == {"hostname": HOST, "service": SERVICE}
    assert tr.change_summary(old, new) == ([{"hostname": HOST, "service": SERVICE}], [])
    assert tr.add_rule(new, HOST, SERVICE) == new


def test_add_rule_refuses_conflicts_and_missing_catch_all():
    with pytest.raises(tr.RouteError):
        tr.add_rule(_ingress()[:-1], HOST, SERVICE)
    with pytest.raises(tr.RouteError):
        tr.add_rule(tr.add_rule(_ingress(), HOST, "http://127.0.0.1:9999"), HOST, SERVICE)


def test_remove_rule_is_the_exact_inverse():
    old = _ingress()
    assert tr.remove_rule(tr.add_rule(old, HOST, SERVICE), HOST) == old
    with pytest.raises(tr.RouteError):
        tr.remove_rule(old, HOST)


def test_dry_run_reports_one_added_rule_and_writes_nothing():
    api = FakeApi(_ingress())
    rc, out = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52")
    assert rc == 0
    assert "ingress: 52 kural -> 53 kural" in out
    assert f'eklenen: 1 {{"hostname": "{HOST}", "service": "{SERVICE}"}}' in out
    assert "\nsilinen: 0\n" in out
    assert "fark: +4 satır, -0 satır" in out
    assert f"dns: {HOST} CNAME {TARGET} (proxied) -> oluşturulacak" in out
    assert out.rstrip().endswith("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı")
    assert api.writes() == []


def test_apply_writes_ingress_then_dns_and_snapshots_the_old_config(tmp_path):
    api = FakeApi(_ingress())
    rc, out = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 0 and out.rstrip().endswith("UYGULANDI")
    assert api.writes() == ["put_tunnel_config", "create_cname"]
    assert api.config["ingress"] == tr.add_rule(_ingress(), HOST, SERVICE)
    assert api.config["warp-routing"] == {"enabled": False}
    assert api.records == [{"id": "rec-1", "type": "CNAME", "name": HOST, "content": TARGET, "proxied": True}]
    snapshots = list(tmp_path.glob("hp-ai-node-config-*.json"))
    assert len(snapshots) == 1 and snapshots[0].stat().st_mode & 0o777 == 0o600
    assert json.loads(snapshots[0].read_text())["ingress"] == _ingress()


def test_apply_refuses_when_rule_count_drifted_or_backup_dir_missing(tmp_path):
    drifted = FakeApi(_ingress(52))
    assert _run(drifted, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula",
                "--yedek-dizini", str(tmp_path))[0] == 2
    no_backup = FakeApi(_ingress())
    assert _run(no_backup, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula")[0] == 2
    assert drifted.writes() == [] and no_backup.writes() == []


def test_foreign_dns_record_is_never_overwritten(tmp_path):
    api = FakeApi(_ingress(), records=[{"id": "x", "type": "A", "name": HOST, "content": "192.0.2.1", "proxied": False}])
    rc, _ = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 2 and api.writes() == []


def test_remove_deletes_dns_before_ingress_and_restores_the_pre_state(tmp_path):
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path / "a"))
    api.calls.clear()
    rc, out = _run(api, "kaldir", "--beklenen-kural", "53", "--uygula", "--yedek-dizini", str(tmp_path / "b"))
    assert rc == 0 and "fark: +0 satır, -4 satır" in out
    assert api.writes() == ["delete_dns_record", "put_tunnel_config"]
    assert api.config["ingress"] == _ingress() and api.records == []


def test_verify_against_snapshot_catches_any_other_change(tmp_path):
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    snapshot = next(tmp_path.glob("*.json"))
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var", "--yedek", str(snapshot))
    assert rc == 0 and "ingress: 53 kural" in out and out.rstrip().endswith("DOĞRULANDI")
    api.config["ingress"][0]["service"] = "http://localhost:9999"
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var", "--yedek", str(snapshot))
    assert rc == 1 and "SORUN yedeğe göre sapma" in out


def test_verify_absent_state():
    api = FakeApi(_ingress())
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "yok")
    assert rc == 0 and f"{HOST}: yok" in out and "dns: yok" in out
    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var")
    assert rc == 1 and "DOĞRULANAMADI" in out


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code, self._payload = status, payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response, self.requests = response, []

    def request(self, method, url, **kw):
        self.requests.append((method, url, kw))
        return self.response


def test_api_resolves_by_name_handles_missing_and_hides_the_token():
    ok = FakeSession(FakeResponse(200, {"success": True, "result": [{"id": "z1", "account": {"id": "a1"}}]}))
    assert tr.CloudflareApi("secret-token-value", session=ok).zone("tedy.online") == ("z1", "a1")
    method, url, kw = ok.requests[0]
    assert (method, url, kw["params"]) == ("GET", "https://api.cloudflare.com/client/v4/zones", {"name": "tedy.online"})
    denied = tr.CloudflareApi("secret-token-value", session=FakeSession(
        FakeResponse(403, {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]})))
    with pytest.raises(tr.RouteError) as exc:
        denied.tunnel_id("a1", "hp-ai-node")
    assert "10000" in str(exc.value) and "secret-token-value" not in str(exc.value)
    missing = tr.CloudflareApi("t", session=FakeSession(
        FakeResponse(404, {"success": False, "errors": [{"code": 10003, "message": "not found"}]})))
    assert missing.call("GET", "/zones/z1/rulesets/phases/http_ratelimit/entrypoint", missing_ok=True) is None
    with pytest.raises(tr.RouteError):
        tr.CloudflareApi("")
