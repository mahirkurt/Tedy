"""Prepare TED's .env for ted-mcp without ever printing a secret value.

    .venv/bin/python -m src.mcp_server.env_prep durum
    .venv/bin/python -m src.mcp_server.env_prep ayarla TED_MCP_FORM_SECRET --uret
    doppler secrets get ANAMNESIS_MCP_API_KEY --plain --project cureohub --config dev_personal \
      | .venv/bin/python -m src.mcp_server.env_prep ayarla ANAMNESIS_MCP_API_KEY --stdin
    .venv/bin/python -m src.mcp_server.env_prep dashboard-anahtari --etiket ted-mcp
    .venv/bin/python -m src.mcp_server.env_prep kaldir TED_MCP_FORM_SECRET
    .venv/bin/python -m src.mcp_server.env_prep dashboard-anahtari-kaldir --etiket ted-mcp

The file is read by two parsers that disagree on edge cases: src/env_loader.py (first
occurrence wins, no quoting) and systemd EnvironmentFile= (last occurrence wins, quotes and
escapes). Values are therefore unquoted and restricted to a safe alphabet, and duplicates are
reported. Writes are atomic, keep mode 0600 and follow a symlinked .env (git worktrees link
it) instead of replacing the link with a regular file.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path
from typing import TextIO

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OPTIONAL = ("ANAMNESIS_MCP_API_KEY", "MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY")
# Non-secret deployment settings live in ted-mcp.service Environment= lines. systemd lets
# EnvironmentFile= override Environment=, so any of these in .env would silently beat the unit.
TOPOLOGY = ("TED_MCP_HOST", "TED_MCP_PORT", "TED_MCP_PUBLIC_BASE_URL", "TED_MCP_ALLOWED_HOSTS",
            "TED_DASHBOARD_API_URL")
UNIT_ONLY = TOPOLOGY + ("TED_MCP_PROJECT_ROOT", "TED_MCP_MAX_BODY_BYTES", "TED_MCP_EXTRA_REDIRECT_URIS",
                        "TED_MCP_EXTRA_FORM_ACTION_ORIGINS")
DASHBOARD_KEY_LABEL = "ted-mcp"
MIN_FORM_SECRET_BYTES = 32

_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_VALUE_RE = re.compile(r"^[A-Za-z0-9._~+/=-]+$")
_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class EnvPrepError(Exception):
    pass


def _name_of(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def parse(lines: list[str]) -> dict[str, list[str]]:
    """Every value per name in file order; duplicates are kept so they can be reported."""
    found: dict[str, list[str]] = {}
    for line in lines:
        name = _name_of(line)
        if name is not None:
            found.setdefault(name, []).append(line.strip().split("=", 1)[1].strip())
    return found


def _first(values: dict[str, list[str]], name: str) -> str:
    return (values.get(name) or [""])[0]


def _append(lines: list[str], new_line: str) -> list[str]:
    out = list(lines)
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    return out + [new_line]


def set_value(lines: list[str], name: str, value: str, replace: bool = False) -> list[str]:
    if not _NAME_RE.match(name):
        raise EnvPrepError(f"geçersiz ad: {name}")
    if name in UNIT_ONLY:
        raise EnvPrepError(f"{name} .env'e yazılmaz; ted-mcp.service Environment= satırında durur")
    if not _VALUE_RE.match(value):
        raise EnvPrepError(f"{name}: değer boş ya da izin verilmeyen karakter içeriyor")
    indexes = [i for i, line in enumerate(lines) if _name_of(line) == name]
    if len(indexes) > 1:
        raise EnvPrepError(f"{name} birden fazla kez tanımlı; önce elle tekilleştirin")
    if indexes and not replace:
        raise EnvPrepError(f"{name} zaten tanımlı; değiştirmek için --degistir")
    if indexes:
        out = list(lines)
        out[indexes[0]] = f"{name}={value}\n"
        return out
    return _append(lines, f"{name}={value}\n")


def remove_value(lines: list[str], name: str) -> list[str]:
    out = [line for line in lines if _name_of(line) != name]
    if len(out) == len(lines):
        raise EnvPrepError(f"{name} tanımlı değil")
    return out


def _entries(values: dict[str, list[str]]) -> list[str]:
    if len(values.get("API_KEYS", [])) > 1:
        raise EnvPrepError("API_KEYS birden fazla kez tanımlı; önce elle tekilleştirin")
    return [e.strip() for e in _first(values, "API_KEYS").split(",") if e.strip()]


def _label(entry: str) -> str:
    # Mirrors dashboard_api._load_api_keys: "label:key", or a bare key labelled "default".
    return entry.split(":", 1)[0].strip() if ":" in entry else "default"


def _key(entry: str) -> str:
    return entry.split(":", 1)[1].strip() if ":" in entry else entry


def _with_api_keys(lines: list[str], entries: list[str]) -> list[str]:
    indexes = [i for i, line in enumerate(lines) if _name_of(line) == "API_KEYS"]
    if not entries:
        return [line for i, line in enumerate(lines) if i not in indexes]
    new_line = "API_KEYS=" + ",".join(entries) + "\n"
    if indexes:
        out = list(lines)
        out[indexes[0]] = new_line
        return out
    return _append(lines, new_line)


def add_dashboard_key(lines: list[str], label: str, key: str) -> list[str]:
    if not _LABEL_RE.match(label):
        raise EnvPrepError(f"geçersiz etiket: {label}")
    if not key.startswith("tdyK_") or not _VALUE_RE.match(key):
        raise EnvPrepError("dashboard anahtarı tdyK_ ile başlamalı")
    entries = _entries(parse(lines))
    if any(_label(e) == label for e in entries):
        raise EnvPrepError(f"API_KEYS içinde '{label}' etiketi zaten var")
    lines = set_value(lines, "TED_DASHBOARD_API_KEY", key)
    return _with_api_keys(lines, entries + [f"{label}:{key}"])


def remove_dashboard_key(lines: list[str], label: str) -> list[str]:
    values = parse(lines)
    entries = _entries(values)
    removed = {_key(e) for e in entries if _label(e) == label}
    if not removed:
        raise EnvPrepError(f"API_KEYS içinde '{label}' etiketi yok")
    lines = _with_api_keys(lines, [e for e in entries if _label(e) != label])
    if _first(values, "TED_DASHBOARD_API_KEY") in removed:
        lines = remove_value(lines, "TED_DASHBOARD_API_KEY")
    return lines


def status(lines: list[str]) -> tuple[list[str], bool]:
    """Readiness report with names and verdicts only — never a value."""
    values = parse(lines)
    report: list[str] = []
    for name, found in values.items():
        if len(found) > 1:
            report.append(f"HATA {name}: {len(found)} kez tanımlı (env_loader ilkini, systemd sonuncuyu alır)")
    secret = _first(values, "TED_MCP_FORM_SECRET")
    if not secret:
        report.append("EKSIK TED_MCP_FORM_SECRET")
    elif len(secret.encode("utf-8")) < MIN_FORM_SECRET_BYTES:
        report.append(f"HATA TED_MCP_FORM_SECRET: {MIN_FORM_SECRET_BYTES} bayttan kısa")
    else:
        report.append("TAMAM TED_MCP_FORM_SECRET")
    dash = _first(values, "TED_DASHBOARD_API_KEY")
    try:
        labelled = [_key(e) for e in _entries(values) if _label(e) == DASHBOARD_KEY_LABEL]
    except EnvPrepError:
        labelled = []
    if not dash:
        report.append("EKSIK TED_DASHBOARD_API_KEY")
    elif not dash.startswith("tdyK_") or labelled != [dash]:
        report.append(f"HATA TED_DASHBOARD_API_KEY: API_KEYS içindeki '{DASHBOARD_KEY_LABEL}' girdisiyle eşleşmiyor")
    else:
        report.append("TAMAM TED_DASHBOARD_API_KEY")
    for name in OPTIONAL:
        report.append(f"{'VAR' if _first(values, name) else 'YOK'} {name}")
    for name in UNIT_ONLY:
        if name in values:
            report.append(f"HATA {name}: .env'de olmamalı (ted-mcp.service Environment=)")
    ok = not any(row.startswith(("HATA", "EKSIK")) for row in report)
    return report, ok


def read_env(path: Path) -> list[str]:
    real = Path(os.path.realpath(path))
    if not real.exists():
        return []
    return real.read_text(encoding="utf-8").splitlines(keepends=True)


def write_env(path: Path, lines: list[str]) -> None:
    real = Path(os.path.realpath(path))
    fd, tmp = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=real.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.writelines(lines)
        os.chmod(tmp, 0o600)
        os.replace(tmp, real)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def main(argv: list[str] | None = None, stdin: TextIO | None = None, out: TextIO | None = None) -> int:
    stdin = sys.stdin if stdin is None else stdin
    out = sys.stdout if out is None else out
    parser = argparse.ArgumentParser(description="ted-mcp .env hazırlığı (değerler asla yazdırılmaz)")
    parser.add_argument("--env", type=Path, default=PROJECT_ROOT / ".env")
    sub = parser.add_subparsers(dest="komut", required=True)
    sub.add_parser("durum")
    ayarla = sub.add_parser("ayarla")
    ayarla.add_argument("ad")
    source = ayarla.add_mutually_exclusive_group(required=True)
    source.add_argument("--uret", action="store_true", help="secrets.token_hex(32)")
    source.add_argument("--stdin", action="store_true", help="değeri standart girdinin ilk satırından oku")
    ayarla.add_argument("--degistir", action="store_true")
    kaldir = sub.add_parser("kaldir")
    kaldir.add_argument("ad")
    for name in ("dashboard-anahtari", "dashboard-anahtari-kaldir"):
        sub.add_parser(name).add_argument("--etiket", default=DASHBOARD_KEY_LABEL)
    args = parser.parse_args(argv)

    lines = read_env(args.env)
    if args.komut == "durum":
        report, ok = status(lines)
        for row in report:
            print(row, file=out)
        return 0 if ok else 1
    try:
        if args.komut == "ayarla":
            value = secrets.token_hex(32) if args.uret else stdin.readline().strip()
            new = set_value(lines, args.ad, value, replace=args.degistir)
            message = f"yazıldı: {args.ad}"
        elif args.komut == "kaldir":
            new = remove_value(lines, args.ad)
            message = f"kaldırıldı: {args.ad}"
        elif args.komut == "dashboard-anahtari":
            new = add_dashboard_key(lines, args.etiket, f"tdyK_{secrets.token_urlsafe(32)}")
            message = f"yazıldı: TED_DASHBOARD_API_KEY ve API_KEYS içindeki '{args.etiket}' girdisi"
        else:
            new = remove_dashboard_key(lines, args.etiket)
            message = f"kaldırıldı: API_KEYS içindeki '{args.etiket}' girdisi"
    except EnvPrepError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2
    write_env(args.env, new)
    print(message, file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
