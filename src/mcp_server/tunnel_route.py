"""Add or remove one hostname route on a remotely managed Cloudflare tunnel — merge-only.

    .venv/bin/python -m src.mcp_server.tunnel_route --bolge tedy.online --tunel hp-ai-node \
        --host mcp.tedy.online ekle --servis http://127.0.0.1:8090 --beklenen-kural 52
    ...  ekle --servis http://127.0.0.1:8090 --beklenen-kural 52 --uygula --yedek-dizini ~/.local/share/ted-backups
    ...  dogrula --servis http://127.0.0.1:8090 --durum var --yedek <yedek.json>
    ...  kaldir --beklenen-kural 53 [--uygula --yedek-dizini DIR]

The zone and the tunnel are resolved by name; CLOUDFLARE_ZONE_ID / CLOUDFLARE_TUNNEL_ID in
TED's .env belong to other resources and are never read. Without --uygula nothing is written.
With --uygula the tool refuses anything other than exactly one added rule (ekle) or one removed
rule (kaldir), never overwrites or deletes a DNS record it did not expect, snapshots the full
tunnel configuration first and re-reads what it wrote. Only CLOUDFLARE_API_TOKEN is read from
the environment, and it is never printed.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Callable, TextIO

import requests

API_BASE = "https://api.cloudflare.com/client/v4"
Rule = dict[str, Any]


class RouteError(Exception):
    pass


def _norm(rule: Rule) -> Rule:
    # The API may echo empty defaults (e.g. originRequest: {}); they carry no routing meaning.
    return {k: v for k, v in rule.items() if v not in ({}, [], None)}


def _canon(rule: Rule) -> str:
    return json.dumps(_norm(rule), sort_keys=True, ensure_ascii=False)


def _is_catch_all(rule: Rule) -> bool:
    return not rule.get("hostname") and not rule.get("path")


def add_rule(ingress: list[Rule], hostname: str, service: str) -> list[Rule]:
    """Insert {hostname, service} just before the trailing catch-all; other rules are untouched."""
    if not ingress or not _is_catch_all(ingress[-1]):
        raise RouteError("ingress'in son kuralı catch-all değil; elle incelenmeli")
    wanted = {"hostname": hostname, "service": service}
    existing = [r for r in ingress if r.get("hostname") == hostname]
    if not existing:
        return list(ingress[:-1]) + [wanted, ingress[-1]]
    if [_norm(r) for r in existing] == [wanted]:
        return list(ingress)
    raise RouteError(f"{hostname} için farklı bir kural zaten var; elle incelenmeli")


def remove_rule(ingress: list[Rule], hostname: str) -> list[Rule]:
    kept = [r for r in ingress if r.get("hostname") != hostname]
    if len(kept) == len(ingress):
        raise RouteError(f"{hostname} için ingress kuralı yok")
    return kept


def change_summary(old: list[Rule], new: list[Rule]) -> tuple[list[Rule], list[Rule]]:
    """(added, removed), comparing normalised rules as multisets."""
    remaining = [_canon(r) for r in old]
    added: list[Rule] = []
    for rule in new:
        key = _canon(rule)
        if key in remaining:
            remaining.remove(key)
        else:
            added.append(_norm(rule))
    return added, [json.loads(k) for k in remaining]


def ingress_diff(old: list[Rule], new: list[Rule]) -> str:
    def lines(rules: list[Rule]) -> list[str]:
        return (json.dumps(rules, indent=2, sort_keys=True, ensure_ascii=False) + "\n").splitlines(keepends=True)

    return "".join(difflib.unified_diff(lines(old), lines(new), fromfile="mevcut", tofile="onerilen"))


def dns_state(records: list[dict[str, Any]], hostname: str, target: str) -> str:
    """'yok' or 'doğru'; any other record set raises, so a foreign record is never touched."""
    if not records:
        return "yok"
    if (len(records) == 1 and records[0].get("type") == "CNAME"
            and records[0].get("content") == target and records[0].get("proxied") is True):
        return "doğru"
    kinds = [(r.get("type"), r.get("proxied")) for r in records]
    raise RouteError(f"{hostname} için beklenmeyen DNS kaydı {kinds}; elle incelenmeli")


class CloudflareApi:
    def __init__(self, token: str, session: Any = None, base: str = API_BASE, timeout: float = 20.0) -> None:
        if not token:
            raise RouteError("CLOUDFLARE_API_TOKEN tanımlı değil")
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self._session = session if session is not None else requests.Session()
        self._base = base
        self._timeout = timeout

    def call(self, method: str, path: str, params: dict[str, str] | None = None, body: Any = None,
             missing_ok: bool = False) -> Any:
        try:
            resp = self._session.request(method, self._base + path, headers=self._headers,
                                         params=params, json=body, timeout=self._timeout)
        except requests.RequestException as exc:
            raise RouteError(f"{method} {path}: {type(exc).__name__}") from None
        if missing_ok and resp.status_code == 404:
            return None
        try:
            data = resp.json()
        except ValueError:
            raise RouteError(f"{method} {path}: JSON olmayan yanıt (HTTP {resp.status_code})") from None
        if not isinstance(data, dict) or not data.get("success"):
            errors = data.get("errors") if isinstance(data, dict) else None
            summary = [(e.get("code"), e.get("message")) for e in errors or [] if isinstance(e, dict)]
            raise RouteError(f"{method} {path}: HTTP {resp.status_code} {summary}")
        return data.get("result")

    def zone(self, name: str) -> tuple[str, str]:
        zones = self.call("GET", "/zones", params={"name": name}) or []
        if len(zones) != 1:
            raise RouteError(f"bölge bulunamadı ya da birden fazla: {name}")
        return zones[0]["id"], zones[0]["account"]["id"]

    def tunnel_id(self, account_id: str, name: str) -> str:
        tunnels = self.call("GET", f"/accounts/{account_id}/cfd_tunnel", params={"name": name, "is_deleted": "false"}) or []
        matches = [t for t in tunnels if t.get("name") == name]
        if len(matches) != 1:
            raise RouteError(f"tünel bulunamadı ya da birden fazla: {name}")
        return matches[0]["id"]

    def tunnel_config(self, account_id: str, tunnel_id: str) -> dict[str, Any]:
        result = self.call("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations") or {}
        config = result.get("config")
        if not isinstance(config, dict) or not isinstance(config.get("ingress"), list):
            raise RouteError("tünel yapılandırması okunamadı (uzaktan yönetilen bir tünel mi?)")
        return config

    def put_tunnel_config(self, account_id: str, tunnel_id: str, config: dict[str, Any]) -> None:
        self.call("PUT", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations", body={"config": config})

    def dns_records(self, zone_id: str, name: str) -> list[dict[str, Any]]:
        return list(self.call("GET", f"/zones/{zone_id}/dns_records", params={"name": name}) or [])

    def create_cname(self, zone_id: str, name: str, target: str) -> dict[str, Any]:
        return self.call("POST", f"/zones/{zone_id}/dns_records", body={
            "type": "CNAME", "name": name, "content": target, "proxied": True, "ttl": 1,
            "comment": "ted-mcp (alt proje 3)"})

    def delete_dns_record(self, zone_id: str, record_id: str) -> None:
        self.call("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")


def default_api() -> CloudflareApi:
    from src.env_loader import load_env

    load_env()
    return CloudflareApi(os.environ.get("CLOUDFLARE_API_TOKEN", "").strip())


def write_snapshot(directory: Path, stem: str, payload: Any, now: float) -> Path:
    directory = directory.expanduser()
    try:
        # M-2: Check existing directory permissions before creating
        if directory.exists():
            mode = directory.stat().st_mode & 0o777
            if mode & 0o077:
                raise RouteError(f"yedek dizinin izinleri çok açık (mode {oct(mode)}); elle denetleyin")
        else:
            # R2-4: Ensure all directory components (including missing parents) get 0700
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            # chmod all parent directories to 0700 that were just created
            current = directory
            while current != current.parent:
                try:
                    st_mode = current.stat().st_mode & 0o777
                    if st_mode != 0o700:
                        current.chmod(0o700)
                except OSError:
                    pass
                current = current.parent
    except OSError as exc:
        # R2-5: Removed dead isinstance check; RouteError is never caught by except OSError
        raise RouteError(f"yedek dizini oluşturulamadı: {exc.strerror if hasattr(exc, 'strerror') else str(exc)}")

    # M-1: Avoid same-second filename collisions with random suffix
    timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(now))
    suffix_str = secrets.token_hex(2)  # 4 hex chars = 2 bytes
    path = directory / f"{stem}-{timestamp}-{suffix_str}.json"

    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
        return path
    except OSError as exc:
        raise RouteError(f"yedek dosyası yazılamadı: {exc.strerror if hasattr(exc, 'strerror') else str(exc)}")


def _put_and_confirm(api: CloudflareApi, account_id: str, tunnel_id: str, config: dict[str, Any],
                     ingress: list[Rule]) -> None:
    # M-4: Re-read config before PUT to detect concurrent changes
    current_config = api.tunnel_config(account_id, tunnel_id)
    current_ingress = current_config.get("ingress", [])
    if [_norm(r) for r in current_ingress] != [_norm(r) for r in config.get("ingress", [])]:
        raise RouteError("tünel yapılandırması arasında değişmiş; tekrar deneyin")

    api.put_tunnel_config(account_id, tunnel_id, {**config, "ingress": ingress})
    reread = api.tunnel_config(account_id, tunnel_id)["ingress"]
    if [_norm(r) for r in reread] != [_norm(r) for r in ingress]:
        raise RouteError("ingress yazıldı ama yeniden okunan kurallar beklenenden farklı; yedekle karşılaştırın")


def _print_plan(out: TextIO, args: argparse.Namespace, zone_id: str, tunnel_id: str,
                old: list[Rule], new: list[Rule], dns_line: str) -> None:
    added, removed = change_summary(old, new)
    diff = ingress_diff(old, new)
    plus = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    minus = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    print(f"bölge: {args.bolge} ({zone_id})", file=out)
    print(f"tünel: {args.tunel} ({tunnel_id})", file=out)
    print(f"ingress: {len(old)} kural -> {len(new)} kural", file=out)
    print(" ".join([f"eklenen: {len(added)}", *(_canon(r) for r in added)]), file=out)
    print(" ".join([f"silinen: {len(removed)}", *(_canon(r) for r in removed)]), file=out)
    print(f"fark: +{plus} satır, -{minus} satır", file=out)
    print(f"dns: {dns_line}", file=out)
    print(diff, end="", file=out)


def _verify(args: argparse.Namespace, out: TextIO, current: list[Rule], records: list[dict[str, Any]],
            target: str) -> int:
    problems: list[str] = []
    mine = [_norm(r) for r in current if r.get("hostname") == args.host]
    if args.durum == "var" and mine != [{"hostname": args.host, "service": args.servis}]:
        problems.append(f"ingress: {args.host} tam bir kez ve {args.servis} ile bulunmalı")
    if args.durum == "yok" and mine:
        problems.append(f"ingress: {args.host} kuralı hâlâ var")
    if not current or not _is_catch_all(current[-1]):
        problems.append("ingress: son kural catch-all değil")
    try:
        dns = dns_state(records, args.host, target)
    except RouteError as exc:
        problems.append(str(exc))
        dns = "beklenmeyen"
    wanted = "doğru" if args.durum == "var" else "yok"
    if dns != wanted:
        problems.append(f"dns: beklenen {wanted}, bulunan {dns}")
    if args.yedek is not None:
        snapshot = json.loads(args.yedek.expanduser().read_text(encoding="utf-8"))["ingress"]
        if args.durum == "var":
            expected = add_rule(snapshot, args.host, args.servis)
        elif any(r.get("hostname") == args.host for r in snapshot):
            expected = remove_rule(snapshot, args.host)
        else:
            expected = snapshot
        if [_norm(r) for r in current] != [_norm(r) for r in expected]:
            extra, missing = change_summary(expected, current)
            # M-3: Detect rule reordering (fazla=0, eksik=0 but lists differ)
            if len(extra) == 0 and len(missing) == 0:
                problems.append("yedeğe göre sapma: kural sırası farklı")
            else:
                problems.append(f"yedeğe göre sapma: fazla {len(extra)}, eksik {len(missing)} kural (sıra da karşılaştırılır)")
    print(f"ingress: {len(current)} kural", file=out)
    print(f"{args.host}: {'var' if mine else 'yok'}", file=out)
    print(f"dns: {dns}", file=out)
    for problem in problems:
        print(f"SORUN {problem}", file=out)
    print("DOĞRULANAMADI" if problems else "DOĞRULANDI", file=out)
    return 1 if problems else 0


def main(argv: list[str] | None = None, api: CloudflareApi | None = None, out: TextIO | None = None,
         clock: Callable[[], float] = time.time) -> int:
    out = sys.stdout if out is None else out
    parser = argparse.ArgumentParser(description="Cloudflare tüneline tek hostname rotasını birleştirerek ekle/kaldır")
    parser.add_argument("--bolge", required=True, help="DNS bölgesi adı, örn. tedy.online")
    parser.add_argument("--tunel", required=True, help="tünel adı, örn. hp-ai-node")
    parser.add_argument("--host", required=True, help="yayınlanacak hostname")
    sub = parser.add_subparsers(dest="komut", required=True)
    ekle = sub.add_parser("ekle")
    ekle.add_argument("--servis", required=True)
    kaldir = sub.add_parser("kaldir")
    for command in (ekle, kaldir):
        command.add_argument("--beklenen-kural", type=int, required=True)
        command.add_argument("--uygula", action="store_true")
        command.add_argument("--yedek-dizini", type=Path)
    dogrula = sub.add_parser("dogrula")
    dogrula.add_argument("--servis", required=True)
    dogrula.add_argument("--durum", choices=("var", "yok"), required=True)
    dogrula.add_argument("--yedek", type=Path)
    args = parser.parse_args(argv)

    try:
        api = api if api is not None else default_api()
        zone_id, account_id = api.zone(args.bolge)
        tunnel_id = api.tunnel_id(account_id, args.tunel)
        target = f"{tunnel_id}.cfargotunnel.com"
        config = api.tunnel_config(account_id, tunnel_id)
        old = config["ingress"]
        records = api.dns_records(zone_id, args.host)
        if args.komut == "dogrula":
            return _verify(args, out, old, records, target)

        adding = args.komut == "ekle"
        new = add_rule(old, args.host, args.servis) if adding else remove_rule(old, args.host)
        dns = dns_state(records, args.host, target)
        action = {(True, "yok"): "oluşturulacak", (True, "doğru"): "zaten doğru",
                  (False, "doğru"): "silinecek", (False, "yok"): "zaten yok"}[(adding, dns)]
        _print_plan(out, args, zone_id, tunnel_id, old, new, f"{args.host} CNAME {target} (proxied) -> {action}")
        if len(old) != args.beklenen_kural:
            raise RouteError(f"kural sayısı değişmiş: ölçülen {len(old)}, beklenen {args.beklenen_kural}")
        if not args.uygula:
            print("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı", file=out)
            return 0
        added, removed = change_summary(old, new)
        if (len(added), len(removed)) != ((1, 0) if adding else (0, 1)):
            raise RouteError(f"kilit: {len(added)} eklenen, {len(removed)} silinen kural; tam bir değişiklik bekleniyordu")
        if args.yedek_dizini is None:
            raise RouteError("--uygula için --yedek-dizini zorunlu")
        print(f"yedek: {write_snapshot(args.yedek_dizini, f'{args.tunel}-config', config, clock())}", file=out)
        if adding:
            _put_and_confirm(api, account_id, tunnel_id, config, new)
            print("ingress: yazıldı ve yeniden okunarak doğrulandı", file=out)
            if dns == "yok":
                api.create_cname(zone_id, args.host, target)
        else:
            # I-2: kaldir order: DNS first for security, then ingress
            dns_deleted = False
            try:
                for record in records if dns == "doğru" else []:
                    api.delete_dns_record(zone_id, record["id"])
                dns_deleted = dns == "doğru"
                _put_and_confirm(api, account_id, tunnel_id, config, new)
            except RouteError as exc:
                # I-2(b)/R2-2: If DNS was deleted but PUT failed, tell operator explicitly with cause
                if dns_deleted:
                    raise RouteError(f"kısmi başarısızlık: DNS kaydı silindi ama ingress kuralı hâlâ var; "
                                   f"aynı kaldir komutunu tekrar çalıştırın; neden: {exc}") from None
                raise
            print("ingress: yazıldı ve yeniden okunarak doğrulandı", file=out)
        final = dns_state(api.dns_records(zone_id, args.host), args.host, target)
        wanted = "doğru" if adding else "yok"
        if final != wanted:
            raise RouteError(f"dns: beklenen {wanted}, bulunan {final}")
        print(f"dns: {final}", file=out)
        print("UYGULANDI", file=out)
        return 0
    except RouteError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
