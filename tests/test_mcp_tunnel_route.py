"""tunnel_route: merge-only ingress edits with a one-rule interlock, DNS never clobbered, token never printed."""
import io
import json
import os

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


# Fix round 1: I-1 — test the "exactly one change" lock
def test_change_lock_refuses_multiple_rules_removed(tmp_path):
    """The ingress has the target hostname twice; remove_rule removes both, violating the lock."""
    base = _ingress()
    # Add the target hostname once (as if it was added before)
    ingress_with_rule = list(base[:-1]) + [{"hostname": HOST, "service": SERVICE}, base[-1]]
    # Add it again to create a duplicate
    double_rule = list(ingress_with_rule[:-1]) + [{"hostname": HOST, "service": SERVICE}, ingress_with_rule[-1]]
    # Now we have 2 rules with hostname=HOST in the ingress, and 54 total rules
    assert sum(1 for r in double_rule if r.get("hostname") == HOST) == 2
    api = FakeApi(double_rule)
    rc, out = _run(api, "kaldir", "--beklenen-kural", "54", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 2, f"Expected rc 2 (lock error), got rc {rc}. Output: {out}"
    assert api.writes() == [], "Should not write anything when lock fails"


# Fix round 1: I-2(a) — recovery test for partial kaldir failure
def test_kaldir_partial_failure_recovery(tmp_path):
    """After DNS delete succeeds and ingress PUT fails, re-running completes."""
    api = FakeApi(_ingress())
    # First, add a rule successfully
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path / "a"))
    api.calls.clear()

    # Now simulate a partial kaldir: DNS delete succeeds, but PUT will fail
    class FailingPutApi:
        def __init__(self, base_api):
            self.base_api = base_api
            self.put_attempted = False

        def zone(self, name):
            return self.base_api.zone(name)

        def tunnel_id(self, account_id, name):
            return self.base_api.tunnel_id(account_id, name)

        def tunnel_config(self, account_id, tunnel_id):
            return self.base_api.tunnel_config(account_id, tunnel_id)

        def put_tunnel_config(self, account_id, tunnel_id, config):
            self.put_attempted = True
            raise tr.RouteError("simulated PUT failure")

        def dns_records(self, zone_id, name):
            return self.base_api.dns_records(zone_id, name)

        def create_cname(self, zone_id, name, target):
            return self.base_api.create_cname(zone_id, name, target)

        def delete_dns_record(self, zone_id, record_id):
            return self.base_api.delete_dns_record(zone_id, record_id)

    failing_api = FailingPutApi(api)
    rc, _ = _run(failing_api, "kaldir", "--beklenen-kural", "53", "--uygula", "--yedek-dizini", str(tmp_path / "b"))
    assert rc == 2 and failing_api.put_attempted, "PUT should have failed"
    assert api.records == [], "DNS should have been deleted before PUT failure"

    # Re-run the same kaldir on the original api — now DNS is gone, so it should complete
    rc, out = _run(api, "kaldir", "--beklenen-kural", "53", "--uygula", "--yedek-dizini", str(tmp_path / "c"))
    assert rc == 0 and "UYGULANDI" in out, f"Recovery should succeed. Output: {out}"
    assert api.config["ingress"] == _ingress(), "Ingress should be restored to original state"


# Fix round 1: M-1 — snapshot filename collision and OSError handling
def test_write_snapshot_handles_collision_suffix(tmp_path):
    """write_snapshot avoids same-second collisions with random suffix."""
    # Test successful write with collision suffix
    payload = {"test": "data"}
    # Use 1789430400.0 (2026-09-15T00:00:00Z) - same as the test's clock
    now = 1789430400.0
    path1 = tr.write_snapshot(tmp_path, "test", payload, now)
    path2 = tr.write_snapshot(tmp_path, "test", payload, now)  # Same second
    assert path1 != path2, "Collision suffix should make filenames different"
    assert json.loads(path1.read_text()) == payload
    assert json.loads(path2.read_text()) == payload
    # Both filenames should have the timestamp
    assert "20260915T000000Z" in str(path1)
    assert "20260915T000000Z" in str(path2)


# Fix round 1: M-2 — backup directory permission check
def test_write_snapshot_refuses_loose_directory_perms(tmp_path):
    """If backup directory exists with loose perms, refuse before writing."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir(mode=0o777)  # Loose permissions

    with pytest.raises(tr.RouteError) as exc:
        tr.write_snapshot(existing_dir, "test", {"data": 1}, 1000.0)
    assert "izin" in str(exc.value).lower() or "permission" in str(exc.value).lower()

    # Newly created directory should stay 0700
    new_dir = tmp_path / "new"
    tr.write_snapshot(new_dir, "test", {"data": 1}, 1000.0)
    assert (new_dir.stat().st_mode & 0o777) == 0o700


# Fix round 1: M-3 — rule reordering detection in verify
def test_verify_reordering_message(tmp_path):
    """When fazla=0 and eksik=0 but lists differ, message says 'kural sırası farklı' (exact phrase)."""
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path / "add"))
    # Reorder a rule (swap two middle rules) but don't add/remove
    api.config["ingress"][1], api.config["ingress"][2] = api.config["ingress"][2], api.config["ingress"][1]
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"ingress": _ingress()}))

    rc, out = _run(api, "dogrula", "--servis", SERVICE, "--durum", "var", "--yedek", str(snapshot))
    assert rc == 1, f"Should fail verification. Output: {out}"
    # R2-1: Assert exact phrase and absence of "fazla 0, eksik 0"
    assert "kural sırası farklı" in out, f"Should mention 'kural sırası farklı' (exact). Output: {out}"
    assert "fazla 0, eksik 0" not in out, f"Should NOT say 'fazla 0, eksik 0' for reordering. Output: {out}"


# Fix round 1: M-4 — config changed in between PUT
def test_reread_before_put_detects_concurrent_change(tmp_path):
    """If tunnel config changes between first read and PUT, abort with rc 2."""
    class ChangingApi:
        def __init__(self):
            self.config = {"ingress": _ingress(), "warp-routing": {"enabled": False}}
            self.read_count = 0

        def zone(self, name):
            return "zone-tedy", "acct-1"

        def tunnel_id(self, account_id, name):
            return TUNNEL

        def tunnel_config(self, account_id, tunnel_id):
            self.read_count += 1
            if self.read_count == 2:
                # Second read (before PUT) returns a different ingress
                changed = _ingress()
                changed[0]["service"] = "http://localhost:9999"  # Someone else changed it
                return {"ingress": changed, "warp-routing": {"enabled": False}}
            return json.loads(json.dumps(self.config))

        def put_tunnel_config(self, account_id, tunnel_id, config):
            raise RuntimeError("PUT should not be called")

        def dns_records(self, zone_id, name):
            return []

        def create_cname(self, zone_id, name, target):
            pass

        def delete_dns_record(self, zone_id, record_id):
            pass

    api = ChangingApi()
    rc, out = _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path))
    assert rc == 2, f"Should abort with rc 2 on concurrent change. RC: {rc}"
    # The error message goes to stderr, but we check it was rejected
    assert api.read_count == 2, "Should have done the second read before detecting change"


# Fix round 2: R2-2 — kaldir partial failure message with cause, captured from stderr
def test_kaldir_partial_failure_message_with_cause(tmp_path, capsys):
    """Partial kaldir failure message includes DNS state, instruction, and cause."""
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path / "a"))

    class FailingPutApi:
        def __init__(self, base_api):
            self.base_api = base_api
            self.put_attempted = False
        def zone(self, name):
            return self.base_api.zone(name)
        def tunnel_id(self, account_id, name):
            return self.base_api.tunnel_id(account_id, name)
        def tunnel_config(self, account_id, tunnel_id):
            return self.base_api.tunnel_config(account_id, tunnel_id)
        def put_tunnel_config(self, account_id, tunnel_id, config):
            self.put_attempted = True
            raise tr.RouteError("test PUT failure")
        def dns_records(self, zone_id, name):
            return self.base_api.dns_records(zone_id, name)
        def create_cname(self, zone_id, name, target):
            return self.base_api.create_cname(zone_id, name, target)
        def delete_dns_record(self, zone_id, record_id):
            return self.base_api.delete_dns_record(zone_id, record_id)

    failing_api = FailingPutApi(api)
    rc, out = _run(failing_api, "kaldir", "--beklenen-kural", "53", "--uygula", "--yedek-dizini", str(tmp_path / "b"))
    captured = capsys.readouterr()
    assert rc == 2, f"Should fail. RC: {rc}"
    error_msg = captured.err
    # R2-2: Check message contains the required parts and the cause
    assert "DNS kaydı silindi" in error_msg, f"Should mention DNS deleted. Stderr: {error_msg}"
    assert "ingress kuralı hâlâ var" in error_msg, f"Should mention ingress still present. Stderr: {error_msg}"
    assert "aynı kaldir komutunu tekrar çalıştırın" in error_msg, f"Should mention retry. Stderr: {error_msg}"
    assert "test PUT failure" in error_msg, f"Should include cause. Stderr: {error_msg}"


# Fix round 2: R2-3 — OSError on file write converted to RouteError
def test_write_snapshot_oserror_conversion(tmp_path, monkeypatch):
    """write_snapshot converts file-write OSError to RouteError with Turkish message."""
    import errno

    # Monkeypatch os.open to raise EACCES
    original_open = os.open
    def failing_open(*args, **kw):
        if "json" in str(args[0]):  # Only fail for .json files
            raise OSError(errno.EACCES, "Permission denied")
        return original_open(*args, **kw)

    monkeypatch.setattr(os, "open", failing_open)

    with pytest.raises(tr.RouteError) as exc:
        tr.write_snapshot(tmp_path, "test", {"data": 1}, 1789430400.0)

    error_msg = str(exc.value)
    assert "yedek dosyası yazılamadı" in error_msg, f"Should mention file write. Error: {error_msg}"
    assert "Permission denied" in error_msg or "Izin" in error_msg, f"Should include OS error. Error: {error_msg}"
    assert "secret" not in error_msg and "token" not in error_msg, f"Should not expose tokens. Error: {error_msg}"


# Fix round 3: R3-1(f)1 — a pre-existing 0o755 parent is left untouched; only the leaf is created.
def test_write_snapshot_preserves_preexisting_parent_mode(tmp_path):
    """write_snapshot never chmods an ancestor: a 0o755 parent stays 0o755, the new leaf is 0700."""
    parent = tmp_path / "existing_parent"
    parent.mkdir(mode=0o755)
    before = parent.stat().st_mode & 0o777
    assert before == 0o755
    leaf = parent / "leaf"

    tr.write_snapshot(leaf, "test", {"data": 1}, 1789430400.0)

    assert (leaf.stat().st_mode & 0o777) == 0o700
    after = parent.stat().st_mode & 0o777
    assert after == before == 0o755, "the pre-existing ancestor must never be chmodded"


# Fix round 3: R3-1(f)2 — a missing parent raises RouteError and nothing is created (replaces the
# old nested a/b/c test, which relied on parents=True — now forbidden).
def test_write_snapshot_missing_parent_raises_and_creates_nothing(tmp_path):
    """write_snapshot must not use parents=True: a missing grandparent/parent is refused outright."""
    directory = tmp_path / "missing_parent" / "leaf"
    with pytest.raises(tr.RouteError):
        tr.write_snapshot(directory, "test", {"data": 1}, 1789430400.0)
    assert not (tmp_path / "missing_parent").exists(), "nothing should be created on this path"


# Fix round 3: R3-1(f)3 — a symlink leaf is refused via os.lstat, and the symlink's target is
# never touched (this is exactly the C-1 regression: round 2 chmodded through symlinks).
def test_write_snapshot_symlink_leaf_refused_and_target_untouched(tmp_path):
    target = tmp_path / "real_target"
    target.mkdir(mode=0o700)
    marker = target / "marker.txt"
    marker.write_text("keep me")
    link = tmp_path / "link_leaf"
    link.symlink_to(target)

    with pytest.raises(tr.RouteError):
        tr.write_snapshot(link, "test", {"data": 1}, 1789430400.0)

    assert (target.stat().st_mode & 0o777) == 0o700, "the symlink target's mode must be unchanged"
    assert marker.read_text() == "keep me", "the symlink target's content must be unchanged"
    assert list(target.glob("*.json")) == [], "nothing should have been written through the symlink"


# Fix round 3: R3-1(f)4 — an existing leaf with loose permissions is refused, never repaired.
def test_write_snapshot_existing_leaf_loose_perms_refused_and_unchanged(tmp_path):
    directory = tmp_path / "loose_leaf"
    directory.mkdir(mode=0o750)
    before = directory.stat().st_mode & 0o777
    assert before == 0o750

    with pytest.raises(tr.RouteError):
        tr.write_snapshot(directory, "test", {"data": 1}, 1789430400.0)

    after = directory.stat().st_mode & 0o777
    assert after == before == 0o750, "an existing leaf's mode must never be repaired"
    assert list(directory.glob("*.json")) == []


# Fix round 3: O-2/R3-2 — kaldir --uygula variant where the DNS delete succeeds and the M-4
# re-read abort (a concurrent external edit) fires before the PUT; no PUT must happen and the
# stderr message must carry both the partial-failure text and the M-4 cause.
def test_kaldir_dns_deleted_then_m4_abort_reports_cause(tmp_path, capsys):
    api = FakeApi(_ingress())
    _run(api, "ekle", "--servis", SERVICE, "--beklenen-kural", "52", "--uygula", "--yedek-dizini", str(tmp_path / "a"))
    api.calls.clear()

    class ConcurrentChangeApi:
        """Wraps FakeApi; the second tunnel_config read (inside _put_and_confirm) reports a
        different ingress, simulating a concurrent external edit (the M-4 abort)."""

        def __init__(self, base_api):
            self.base_api = base_api
            self.read_count = 0
            self.put_called = False

        def zone(self, name):
            return self.base_api.zone(name)

        def tunnel_id(self, account_id, name):
            return self.base_api.tunnel_id(account_id, name)

        def tunnel_config(self, account_id, tunnel_id):
            self.read_count += 1
            config = self.base_api.tunnel_config(account_id, tunnel_id)
            if self.read_count == 2:
                config["ingress"][0]["service"] = "http://localhost:9999"
            return config

        def put_tunnel_config(self, account_id, tunnel_id, config):
            self.put_called = True
            self.base_api.put_tunnel_config(account_id, tunnel_id, config)

        def dns_records(self, zone_id, name):
            return self.base_api.dns_records(zone_id, name)

        def create_cname(self, zone_id, name, target):
            return self.base_api.create_cname(zone_id, name, target)

        def delete_dns_record(self, zone_id, record_id):
            return self.base_api.delete_dns_record(zone_id, record_id)

    concurrent_api = ConcurrentChangeApi(api)
    rc, out = _run(concurrent_api, "kaldir", "--beklenen-kural", "53", "--uygula",
                   "--yedek-dizini", str(tmp_path / "b"))
    captured = capsys.readouterr()

    assert rc == 2, f"Expected rc 2. Output: {out} Stderr: {captured.err}"
    assert concurrent_api.put_called is False, "no PUT must happen when the M-4 abort fires"
    assert api.records == [], "the DNS delete must have succeeded before the abort"
    error_msg = captured.err
    assert "DNS kaydı silindi" in error_msg, error_msg
    assert "ingress kuralı hâlâ var" in error_msg, error_msg
    assert "aynı kaldir komutunu tekrar çalıştırın" in error_msg, error_msg
    assert "tünel yapılandırması arasında değişmiş" in error_msg, "the M-4 cause must be present: " + error_msg

