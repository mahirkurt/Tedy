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
