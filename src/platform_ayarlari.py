"""Which side platforms TEDY reads — household settings in .env.

SEBİT homework is off while TEDY_SEBIT=0 (asked 2026-10-18: the account's
password was refused and the family set SEBİT aside for now). Off means the
sync makes no login and no surface shows the last reading as current.
"""
import os


def sebit_aktif() -> bool:
    return os.environ.get("TEDY_SEBIT", "1").strip() != "0"
