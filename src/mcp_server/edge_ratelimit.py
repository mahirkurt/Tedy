"""Per-IP edge rate limit for ted-mcp's public endpoints (security review F4), merge-aware.

    .venv/bin/python -m src.mcp_server.edge_ratelimit --bolge tedy.online ekle --beklenen-kural 0
    ...  ekle --beklenen-kural 0 --uygula --yedek-dizini ~/.local/share/ted-backups
    ...  dogrula
    ...  kaldir --beklenen-kural 1 [--uygula --yedek-dizini DIR]

One block rule on the zone's http_ratelimit phase. A Free zone allows a single rate-limiting rule,
so an existing rule gets our condition OR-ed into its expression instead of a second rule. Its
action, threshold and period stay as they are. The merge is refused when the result would break MCP
clients (challenge actions, disabled rule, a threshold below MIN_MERGE_PER_10S, or counting by
something other than ip.src+cf.colo.id — a merge that kept a foreign characteristics set would give
no per-IP protection at all). `--host-kosulu` requires a paid plan and is checked before anything
else; an existing ted-mcp contribution scoped to a different host argument than this invocation
(or the reverse) refuses rather than silently widening or losing the limit. Dry run by default;
--uygula snapshots the phase, re-reads it immediately before PUT to catch a concurrent edit, writes
with PUT and re-reads what it wrote.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, TextIO

from src.mcp_server import tunnel_route
from src.mcp_server.tunnel_route import CloudflareApi, RouteError

PATHS = ("/oauth/register", "/oauth/authorize", "/oauth/token", "/mcp", "/mcp/")
REF = "ted-mcp-hiz-siniri"
DESCRIPTION = "ted-mcp: /oauth/* ve /mcp için IP başına hız sınırı (alt proje 3, güvenlik incelemesi F4)"
DEFAULT_THRESHOLD = 60
PERIOD = 10
TIMEOUT = 10
MIN_MERGE_PER_10S = 30
WRITABLE = ("id", "ref", "action", "action_parameters", "expression", "description", "enabled", "ratelimit", "logging")
REQUIRED_CHARACTERISTICS = ["cf.colo.id", "ip.src"]

# The fixed part of our expression (independent of --host-kosulu), used both to build our_expression()
# and — via _MERGED_SUFFIX_RE — to recognise an existing ted-mcp contribution under ANY host (M-3).
_CONDITION_CORE = "http.request.uri.path in {" + " ".join(f'"{p}"' for p in PATHS) + "}"
_MERGED_SUFFIX_RE = re.compile(r'\) or \((?:http\.host eq "[^"]*" and )?' + re.escape(_CONDITION_CORE) + r"\)$")


def our_expression(host: str | None = None) -> str:
    return f'(http.host eq "{host}" and {_CONDITION_CORE})' if host else f"({_CONDITION_CORE})"


def new_rule(threshold: int, host: str | None = None) -> dict[str, Any]:
    return {"ref": REF, "description": DESCRIPTION, "expression": our_expression(host), "action": "block",
            "ratelimit": {"characteristics": ["ip.src", "cf.colo.id"], "period": PERIOD,
                          "requests_per_period": threshold, "mitigation_timeout": TIMEOUT},
            "enabled": True}


def writable(rule: dict[str, Any]) -> dict[str, Any]:
    # Read-only fields (version, last_updated, …) must not be sent back on PUT.
    return {k: rule[k] for k in WRITABLE if k in rule}


def _suffix(host: str | None) -> str:
    return f") or {our_expression(host)}"


def find_ours(rules: list[dict[str, Any]], host: str | None = None) -> tuple[int, str] | None:
    for i, rule in enumerate(rules):
        expression = rule.get("expression") or ""
        if rule.get("ref") == REF or expression == our_expression(host):
            return i, "ayrı"
        if expression.startswith("(") and expression.endswith(_suffix(host)):
            return i, "birleşik"
    return None


def _any_ted_mcp_contribution(rules: list[dict[str, Any]]) -> int | None:
    """Index of a ted-mcp contribution under ANY host (or none) — unlike `find_ours`, this ignores
    which `--host-kosulu` (if any) it was scoped to. Used only to detect a host mismatch (M-3):
    a wholly-ours rule (`ref == REF`) is host-independent by construction, so it is always also
    found by `find_ours(rules, host)` regardless of `host` and is not a mismatch case. A *merged*
    rule keeps the foreign rule's own fields (no `ref`), so only its expression tail identifies it,
    and that tail encodes the specific host — this catches it under any host value."""
    for i, rule in enumerate(rules):
        if rule.get("ref") == REF:
            return i
        expression = rule.get("expression") or ""
        if expression.startswith("(") and _MERGED_SUFFIX_RE.search(expression):
            return i
    return None


def _check_host_consistency(rules: list[dict[str, Any]], host: str | None) -> None:
    """M-3: refuse before any merge, add or removal if a ted-mcp contribution already exists but
    was scoped to a different --host-kosulu (or lack of one) than this invocation's. Merging under
    the wrong host would add a second, wider OR-branch instead of recognising the existing one;
    removing under the wrong host would silently no-op on the real limit."""
    if _any_ted_mcp_contribution(rules) is not None and find_ours(rules, host) is None:
        raise RouteError("ted-mcp hız sınırı farklı bir host koşuluyla mevcut")


def _characteristics_ok(rule: dict[str, Any]) -> bool:
    limit = rule.get("ratelimit") or {}
    return sorted(limit.get("characteristics") or []) == REQUIRED_CHARACTERISTICS


def essence(rule: dict[str, Any]) -> tuple:
    limit = rule.get("ratelimit") or {}
    return (rule.get("ref"), rule.get("description"), rule.get("expression"), rule.get("action"),
            rule.get("enabled", True), tuple(sorted(limit.get("characteristics") or [])), limit.get("period"),
            limit.get("requests_per_period"), limit.get("mitigation_timeout"))


def describe(rule: dict[str, Any]) -> str:
    limit = rule.get("ratelimit") or {}
    return (f"{rule.get('ref') or rule.get('id')}: {rule.get('action')} "
            f"{limit.get('requests_per_period')}/{limit.get('period')}s, zaman aşımı {limit.get('mitigation_timeout')}s, "
            f"açık={rule.get('enabled', True)}, ifade={rule.get('expression')}")


def add_limit(rules: list[dict[str, Any]], plan: str, threshold: int,
              host: str | None = None) -> tuple[list[dict[str, Any]], str]:
    rules = [writable(r) for r in rules]
    _check_host_consistency(rules, host)
    if find_ours(rules, host) is not None:
        raise RouteError("ted-mcp hız sınırı zaten var; dogrula kullanın")
    if not rules:
        return [new_rule(threshold, host)], "oluştur"
    if plan != "free" or len(rules) != 1:
        raise RouteError(f"{len(rules)} mevcut kural, plan {plan}: otomatik karar yok; elle incelenmeli")
    rule = rules[0]
    limit = rule.get("ratelimit") or {}
    per_10s = limit.get("requests_per_period", 0) * 10 / max(int(limit.get("period") or 10), 1)
    if not _characteristics_ok(rule):
        raise RouteError("mevcut kuralın sayım özellikleri ip.src + cf.colo.id değil; "
                          "IP başına koruma sağlamaz — elle karar")
    if rule.get("action") != "block":
        raise RouteError(f"mevcut kuralın eylemi '{rule.get('action')}'; MCP istemcileri meydan okuma çözemez — elle karar")
    if rule.get("enabled") is False:
        raise RouteError("mevcut kural kapalı; birleştirme koruma sağlamaz — elle karar")
    if per_10s < MIN_MERGE_PER_10S:
        raise RouteError(f"mevcut eşik 10 sn'de {per_10s:g} < {MIN_MERGE_PER_10S}; MCP patlamalarını keser — elle karar")
    return [{**rule, "expression": f"({rule['expression']}) or {our_expression(host)}"}], "birleştir"


def remove_limit(rules: list[dict[str, Any]], host: str | None = None) -> list[dict[str, Any]]:
    rules = [writable(r) for r in rules]
    _check_host_consistency(rules, host)
    found = find_ours(rules, host)
    if found is None:
        raise RouteError("ted-mcp hız sınırı yok")
    i, kind = found
    if kind == "ayrı":
        return rules[:i] + rules[i + 1:]
    expression = rules[i]["expression"]
    return rules[:i] + [{**rules[i], "expression": expression[1:-len(_suffix(host))]}] + rules[i + 1:]


def _entry(zone_id: str) -> str:
    return f"/zones/{zone_id}/rulesets/phases/http_ratelimit/entrypoint"


def _read_rules(api: CloudflareApi, zone_id: str) -> list[dict[str, Any]]:
    entry = api.call("GET", _entry(zone_id), missing_ok=True)
    return list((entry or {}).get("rules") or [])


def _verify(args: argparse.Namespace, out: TextIO, rules: list[dict[str, Any]]) -> int:
    problems: list[str] = []
    found = find_ours(rules, args.host_kosulu)
    if found is None:
        problems.append("ted-mcp hız sınırı yok")
    else:
        i, kind = found
        rule = rules[i]
        print(f"ted-mcp kuralı: {kind}", file=out)
        if rule.get("action") != "block":
            problems.append(f"eylem '{rule.get('action')}', block bekleniyordu")
        if rule.get("enabled") is False:
            problems.append("kural kapalı")
        if not _characteristics_ok(rule):
            problems.append("sayım özellikleri ip.src + cf.colo.id değil")
    for problem in problems:
        print(f"SORUN {problem}", file=out)
    print("DOĞRULANAMADI" if problems else "DOĞRULANDI", file=out)
    return 1 if problems else 0


def main(argv: list[str] | None = None, api: CloudflareApi | None = None, out: TextIO | None = None,
         clock: Callable[[], float] = time.time) -> int:
    out = sys.stdout if out is None else out
    parser = argparse.ArgumentParser(description="ted-mcp uçları için Cloudflare kenar hız sınırı (birleştirme bilinçli)")
    parser.add_argument("--bolge", required=True)
    parser.add_argument("--host-kosulu", default=None, help="yalnız ücretli planda: ifadeye http.host ekler")
    sub = parser.add_subparsers(dest="komut", required=True)
    ekle = sub.add_parser("ekle")
    ekle.add_argument("--esik", type=int, default=DEFAULT_THRESHOLD)
    kaldir = sub.add_parser("kaldir")
    for command in (ekle, kaldir):
        command.add_argument("--beklenen-kural", type=int, required=True)
        command.add_argument("--uygula", action="store_true")
        command.add_argument("--yedek-dizini", type=Path)
    sub.add_parser("dogrula")
    args = parser.parse_args(argv)

    try:
        api = api if api is not None else tunnel_route.default_api()
        zone_id, _ = api.zone(args.bolge)
        plan = str(((api.call("GET", f"/zones/{zone_id}") or {}).get("plan") or {}).get("legacy_id") or "bilinmiyor")
        # M-2: checked before the count lock and the backup — a host condition needs a paid plan,
        # and failing only at PUT would mean a wasted snapshot and a confusing late refusal.
        if args.host_kosulu and plan in ("free", "bilinmiyor"):
            raise RouteError(f"--host-kosulu yalnız ücretli planda kullanılabilir; bu bölgenin planı '{plan}'")
        rules = _read_rules(api, zone_id)
        print(f"bölge: {args.bolge} ({zone_id}), plan: {plan}", file=out)
        print(f"http_ratelimit kuralı: {len(rules)}", file=out)
        for rule in rules:
            print(f"  mevcut: {describe(rule)}", file=out)
        if args.komut == "dogrula":
            return _verify(args, out, rules)
        if args.komut == "ekle":
            new, mode = add_limit(rules, plan, args.esik, args.host_kosulu)
        else:
            new, mode = remove_limit(rules, args.host_kosulu), "kaldır"
        print(f"işlem: {mode}", file=out)
        for rule in new:
            print(f"  sonra: {describe(rule)}", file=out)
        if len(rules) != args.beklenen_kural:
            raise RouteError(f"kural sayısı değişmiş: ölçülen {len(rules)}, beklenen {args.beklenen_kural}")
        if not args.uygula:
            print("KURU ÇALIŞTIRMA: hiçbir şey yazılmadı", file=out)
            return 0
        if args.yedek_dizini is None:
            raise RouteError("--uygula için --yedek-dizini zorunlu")
        snapshot = tunnel_route.write_snapshot(args.yedek_dizini, f"{args.bolge}-ratelimit",
                                               {"zone": args.bolge, "rules": rules}, clock())
        print(f"yedek: {snapshot}", file=out)
        # P5-1: re-read the phase immediately before PUT to catch a concurrent edit; write nothing if it changed.
        current = _read_rules(api, zone_id)
        if [essence(r) for r in current] != [essence(r) for r in rules]:
            raise RouteError("http_ratelimit kural kümesi az önce (yedek alınırken) değişmiş; hiçbir şey yazılmadı, "
                              "tekrar çalıştırın")
        api.call("PUT", _entry(zone_id), body={"rules": new})
        if [essence(r) for r in _read_rules(api, zone_id)] != [essence(r) for r in new]:
            raise RouteError("kurallar yazıldı ama yeniden okunan küme beklenenden farklı; yedekle karşılaştırın")
        print("UYGULANDI", file=out)
        return 0
    except RouteError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
