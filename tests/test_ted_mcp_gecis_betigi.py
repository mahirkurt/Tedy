"""scripts/ted_mcp_sdk2_gecis.sh provası: sahte git deposu, sahte systemctl/pip/curl/journalctl.

Betik canlıda ted-mcp'yi durdurur, main'i ileri sarar ve ortak .venv'e paket kurar. Burada hiçbir canlı yol
kullanılmaz: TED_KOK, TED_PY, TEKERLEKLER, SYSTEMCTL, CURL, JOURNALCTL, GECIS_KAYDI ve HOME tmp_path'e gider.
Asıl soru: başka bir oturumun commit'i main'deyken ya da araya girdiğinde hiçbir şey silinmiyor mu?
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

BETIK = Path(__file__).resolve().parents[1] / "scripts" / "ted_mcp_sdk2_gecis.sh"

_PIP = r'''#!/usr/bin/env bash
S=$STUB_DIR
echo "$*" >> "$S/pip.log"
[ "$1" = "-m" ] && [ "$2" = "pip" ] || exit 9
shift 2; cmd=$1; shift
mcp=$(cat "$S/mcp")
case $cmd in
  freeze)
    echo "anyio==4.12.1"; echo "mcp==$mcp"
    [ -f "$S/extra" ] && { echo "mcp-types==2.3.0"; echo "opentelemetry-api==1.45.1"; }
    echo "starlette==1.3.1"; exit 0 ;;
  check)
    if [ "$mcp" = 2.3.0 ] && [ -n "${STUB_CHECK_BOZUK:-}" ]; then
      echo "mcp 2.3.0 has requirement yok-paket, which is not installed."; exit 1; fi
    echo "No broken requirements found."; exit 0 ;;
  install)
    if printf '%s\n' "$@" | grep -qx -- --dry-run; then
      echo "Would install ${STUB_DRY_RUN:-mcp-2.3.0 mcp-types-2.3.0 opentelemetry-api-1.45.1}"; exit 0; fi
    if printf '%s\n' "$@" | grep -qx "mcp==2.3.0"; then
      if [ -n "${STUB_PIP_DUSER:-}" ]; then
        [ -n "${STUB_PIP_HOOK:-}" ] && bash -c "$STUB_PIP_HOOK"
        echo "ERROR: kurulum düştü" >&2; exit 1; fi
      echo 2.3.0 > "$S/mcp"; touch "$S/extra"; exit 0; fi
    if printf '%s\n' "$@" | grep -qx "mcp==1.28.1"; then echo 1.28.1 > "$S/mcp"; exit 0; fi
    exit 1 ;;
  uninstall) rm -f "$S/extra"; exit 0 ;;
esac
exit 9
'''

_SYSTEMCTL = r'''#!/usr/bin/env bash
echo "$*" >> "$STUB_DIR/systemctl.log"
if [ "$2" = stop ] && [ -n "${STUB_STOP_HOOK:-}" ] && [ ! -f "$STUB_DIR/stop_hook" ]; then
  touch "$STUB_DIR/stop_hook"; bash -c "$STUB_STOP_HOOK"; fi
exit 0
'''

_CURL = r'''#!/usr/bin/env bash
if [ "$(cat "$STUB_DIR/mcp")" = 2.3.0 ] && [ -n "${STUB_2X_COKER:-}" ]; then exit 22; fi
echo '{"status": "ok", "version": "0.1.0"}'
'''

_JOURNALCTL = '#!/usr/bin/env bash\necho "sahte journal: ModuleNotFoundError"\n'


class Prova:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.depo = tmp / "TED"
        self.stub = tmp / "stub"
        self.tek = tmp / "tekerlekler"
        self.kayit = tmp / "kayit"
        for d in (self.depo, self.stub, self.tek):
            d.mkdir()
        for ad, govde in (("python", _PIP), ("systemctl", _SYSTEMCTL), ("curl", _CURL), ("journalctl", _JOURNALCTL)):
            (self.stub / ad).write_text(govde, encoding="utf-8")
            (self.stub / ad).chmod(0o755)
        (self.stub / "mcp").write_text("1.28.1\n", encoding="utf-8")
        ozet = []
        for ad in ("mcp-1.28.1-py3-none-any.whl", "mcp-2.3.0-py3-none-any.whl"):
            (self.tek / ad).write_bytes(ad.encode())
            ozet.append(f"{hashlib.sha256(ad.encode()).hexdigest()}  {ad}\n")
        (self.tek / "SHA256SUMS").write_text("".join(ozet), encoding="ascii")
        (tmp / "gitconfig").write_text("", encoding="utf-8")
        self.env = {
            "PATH": f"{self.stub}:{os.environ['PATH']}", "HOME": str(tmp), "LANG": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(tmp / "gitconfig"),
            "GIT_AUTHOR_NAME": "prova", "GIT_AUTHOR_EMAIL": "prova@example.invalid",
            "GIT_COMMITTER_NAME": "prova", "GIT_COMMITTER_EMAIL": "prova@example.invalid",
            "TED_KOK": str(self.depo), "TED_PY": str(self.stub / "python"), "TEKERLEKLER": str(self.tek),
            "SYSTEMCTL": str(self.stub / "systemctl"), "CURL": str(self.stub / "curl"),
            "JOURNALCTL": str(self.stub / "journalctl"), "SAGLIK_URL": "http://prova.invalid/health",
            "SAGLIK_SURE": "2", "GECIS_KAYDI": str(self.kayit), "STUB_DIR": str(self.stub),
        }
        self.git("init", "-q", "-b", "main")
        (self.depo / "a.txt").write_text("a\n", encoding="utf-8")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "taban")
        self.taban = self.rev("HEAD")
        self.env["BEKLENEN_TABAN"] = self.taban
        self.git("checkout", "-q", "-b", "mcp-sdk-2")
        (self.depo / "b.txt").write_text("b\n", encoding="utf-8")
        self.git("add", "b.txt")
        self.git("commit", "-q", "-m", "sdk 2.3.0")
        self.dal = self.rev("HEAD")
        self.git("checkout", "-q", "main")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.depo, env=self.env, check=True, capture_output=True,
                              text=True).stdout.strip()

    def rev(self, ref: str) -> str:
        return self.git("rev-parse", ref)

    def baska_oturum_commit_komutu(self, mesaj: str) -> str:
        return f"git -C {self.depo} commit -q --allow-empty -m '{mesaj}'"

    def kos(self, **ek: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(BETIK)], cwd=self.tmp, env={**self.env, **ek}, capture_output=True,
                              text=True, timeout=120)

    def systemctl(self) -> list[str]:
        log = self.stub / "systemctl.log"
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def mcp(self) -> str:
        return (self.stub / "mcp").read_text(encoding="utf-8").strip()

    def extra_var(self) -> bool:
        return (self.stub / "extra").exists()

    def mesajlar(self) -> list[str]:
        return self.git("log", "--format=%s", "main").splitlines()


@pytest.fixture
def prova(tmp_path):
    return Prova(tmp_path)


def test_basarili_gecis_ileri_sarar_kurar_baslatir(prova):
    r = prova.kos()
    assert r.returncode == 0, r.stdout + r.stderr
    assert prova.rev("HEAD") == prova.dal
    assert prova.mcp() == "2.3.0" and prova.extra_var()
    assert prova.systemctl() == ["--user stop ted-mcp", "--user reset-failed ted-mcp", "--user start ted-mcp"]
    assert "TAMAM" in r.stdout


def test_baska_oturumun_commiti_onceden_maindeyse_hicbir_sey_yapilmaz(prova):
    prova.git("commit", "-q", "--allow-empty", "-m", "baska oturum")
    onceki = prova.rev("HEAD")
    r = prova.kos()
    assert r.returncode == 1
    assert "main " in r.stdout and "değil" in r.stdout
    assert prova.rev("HEAD") == onceki and prova.mesajlar()[0] == "baska oturum"
    assert prova.systemctl() == [] and prova.mcp() == "1.28.1"


def test_ff_only_araya_giren_commit_yuzunden_duserse_hicbir_sey_silinmez(prova):
    """İnceleme bulgusu: korumasız 'git reset --keep $ONCEKI' burada başka oturumun commit'ini siliyordu."""
    r = prova.kos(STUB_STOP_HOOK=prova.baska_oturum_commit_komutu("durdurma sirasinda baska oturum"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.mesajlar()[:2] == ["durdurma sirasinda baska oturum", "taban"]
    assert "birleştirme main'e girmemiş" in r.stdout and "main'e dokunulmadı" in r.stdout
    assert prova.mcp() == "1.28.1" and not prova.extra_var()
    assert prova.systemctl()[-2:] == ["--user reset-failed ted-mcp", "--user start ted-mcp"]


def test_pip_duserse_yalniz_kendi_birlestirmesini_geri_sarar_ve_eski_kodla_baslatir(prova):
    r = prova.kos(STUB_PIP_DUSER="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.rev("HEAD") == prova.taban
    assert prova.rev("mcp-sdk-2") == prova.dal          # dal yerinde, iş kaybı yok
    assert prova.mcp() == "1.28.1"
    assert prova.systemctl()[-1] == "--user start ted-mcp"


def test_pip_duserken_birlestirmenin_ustune_commit_geldiyse_main_sarilmaz_servis_baslatilmaz(prova):
    r = prova.kos(STUB_PIP_DUSER="1", STUB_PIP_HOOK=prova.baska_oturum_commit_komutu("pip sirasinda baska oturum"))
    assert r.returncode == 3, r.stdout + r.stderr
    assert prova.mesajlar()[:3] == ["pip sirasinda baska oturum", "sdk 2.3.0", "taban"]
    assert "--user start ted-mcp" not in prova.systemctl()
    assert "BAŞLATILMADI" in r.stdout


def test_acilista_cokerse_reset_failed_ile_eski_surume_doner(prova):
    r = prova.kos(STUB_2X_COKER="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.rev("HEAD") == prova.taban
    assert prova.mcp() == "1.28.1" and not prova.extra_var()
    calls = prova.systemctl()
    assert calls.count("--user reset-failed ted-mcp") == 2 and calls[-1] == "--user start ted-mcp"
    assert "ModuleNotFoundError" in (prova.kayit / "journal.txt").read_text(encoding="utf-8")


def test_pip_check_tabana_gore_bozulursa_geri_doner(prova):
    r = prova.kos(STUB_CHECK_BOZUK="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "pip check bozuldu" in r.stdout
    assert prova.rev("HEAD") == prova.taban and prova.mcp() == "1.28.1"
    assert (prova.kayit / "pip-check-oncesi.txt").read_text(encoding="utf-8").startswith("No broken")


def test_dry_run_beklenmeyen_paket_gosterirse_hicbir_sey_yapilmaz(prova):
    r = prova.kos(STUB_DRY_RUN="mcp-2.3.0 mcp-types-2.3.0 opentelemetry-api-1.45.1 starlette-9.9.9")
    assert r.returncode == 1 and "dry-run beklenmeyen" in r.stdout
    assert prova.systemctl() == [] and prova.rev("HEAD") == prova.taban


def test_izlenen_dosyada_kaydedilmemis_degisiklik_varsa_hicbir_sey_yapilmaz(prova):
    (prova.depo / "a.txt").write_text("başka oturumun yarım işi\n", encoding="utf-8")
    r = prova.kos()
    assert r.returncode == 1
    assert (prova.depo / "a.txt").read_text(encoding="utf-8") == "başka oturumun yarım işi\n"
    assert prova.systemctl() == []


def test_tekerlek_ozeti_tutmazsa_hicbir_sey_yapilmaz(prova):
    (prova.tek / "mcp-2.3.0-py3-none-any.whl").write_bytes(b"kurcalanmis")
    r = prova.kos()
    assert r.returncode == 1 and "özetleri tutmuyor" in r.stdout
    assert prova.systemctl() == []
