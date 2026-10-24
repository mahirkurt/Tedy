"""scripts/ted_mcp_sdk2_gecis.sh provası: sahte git deposu, sahte systemctl/pip/curl/journalctl (ve git'i saran sahte).

Betik canlıda ted-mcp'yi durdurur, main'i ileri sarar ve ortak .venv'e paket kurar. Burada hiçbir canlı yol
kullanılmaz: TED_KOK, TED_PY, TEKERLEKLER, SYSTEMCTL, CURL, JOURNALCTL, GECIS_KAYDI ve HOME tmp_path'e gider.
Tekerlek özetleri betiğe gömülü olduğu için gerçek tekerlekler (kalıcı yerinden) kopyalanır; yoksa prova atlanır.
Asıl soru: başka bir oturumun commit'i ya da dalı araya girdiğinde hiçbir şey silinmiyor ve başka dal ileri
sarılmıyor mu? Senaryo adlarındaki s5/s6/s9/s10 üçüncü inceleme turunun bulgularıdır (rapor §13).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

BETIK = Path(__file__).resolve().parents[1] / "scripts" / "ted_mcp_sdk2_gecis.sh"
TEKERLEK_KAYNAGI = Path(os.environ.get("TED_MCP_TEKERLEKLER", "/home/mahirkurt/tekerlekler/ted-mcp-2026-10"))
TEKERLEKLER = ("mcp-1.28.1-py3-none-any.whl", "mcp-2.3.0-py3-none-any.whl", "mcp_types-2.3.0-py3-none-any.whl",
               "opentelemetry_api-1.45.1-py3-none-any.whl")
GERCEK_GIT = shutil.which("git")

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
      [ -n "${STUB_PIP_SINYAL:-}" ] && kill -TERM "$PPID"   # kurulum sürerken betiğe TERM (birim durdurulur gibi)
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
case "$2" in
  stop)
    if [ -n "${STUB_STOP_DUSER:-}" ]; then exit 1; fi
    if [ -n "${STUB_STOP_HOOK:-}" ] && [ ! -f "$STUB_DIR/stop_hook" ]; then
      touch "$STUB_DIR/stop_hook"; bash -c "$STUB_STOP_HOOK"; fi ;;
  is-active)
    echo "${STUB_IS_ACTIVE:-inactive}"; [ "${STUB_IS_ACTIVE:-inactive}" = active ]; exit $? ;;
esac
exit 0
'''

_CURL = r'''#!/usr/bin/env bash
if [ "$(cat "$STUB_DIR/mcp")" = 2.3.0 ] && [ -n "${STUB_2X_COKER:-}" ]; then exit 22; fi
echo '{"status": "ok", "version": "0.1.0"}'
'''

_JOURNALCTL = '#!/usr/bin/env bash\necho "sahte journal: ModuleNotFoundError"\n'

# git'i saran sahte: bayrak dosyasıyla merge-base'i 128 (git hatası) ya da merge'ü düşürür; gerisi gerçek git.
_GIT = r'''#!/usr/bin/env bash
if [ "$1" = merge-base ] && [ -f "$STUB_DIR/mb128" ]; then echo "fatal: sahte merge-base hatası" >&2; exit 128; fi
if [ "$1" = merge ] && [ -f "$STUB_DIR/merge_duser" ]; then echo "fatal: sahte merge hatası" >&2; exit 128; fi
exec "$GERCEK_GIT" "$@"
'''


class Prova:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.depo = tmp / "TED"
        self.stub = tmp / "stub"
        self.tek = tmp / "tekerlekler"
        self.kayit = tmp / "kayit"
        for d in (self.depo, self.stub, self.tek):
            d.mkdir()
        for ad, govde in (("python", _PIP), ("systemctl", _SYSTEMCTL), ("curl", _CURL), ("journalctl", _JOURNALCTL),
                          ("git", _GIT)):
            (self.stub / ad).write_text(govde, encoding="utf-8")
            (self.stub / ad).chmod(0o755)
        (self.stub / "mcp").write_text("1.28.1\n", encoding="utf-8")
        for ad in (*TEKERLEKLER, "SHA256SUMS"):
            shutil.copy2(TEKERLEK_KAYNAGI / ad, self.tek / ad)
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
            "GERCEK_GIT": GERCEK_GIT,
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

    def mesajlar(self, ref: str = "main") -> list[str]:
        return self.git("log", "--format=%s", ref).splitlines()

    def dal_adi(self) -> str:
        return self.git("branch", "--show-current")


@pytest.fixture
def prova(tmp_path):
    if not all((TEKERLEK_KAYNAGI / ad).is_file() for ad in (*TEKERLEKLER, "SHA256SUMS")):
        pytest.skip(f"gerçek tekerlekler yok: {TEKERLEK_KAYNAGI}")
    return Prova(tmp_path)


# -- s1–s4: temel yol ve ön koşullar ---------------------------------------------------------------------

def test_s1_basarili_gecis_ileri_sarar_kurar_baslatir_main_dogrular(prova):
    r = prova.kos()
    assert r.returncode == 0, r.stdout + r.stderr
    assert prova.rev("main") == prova.dal and prova.dal_adi() == "main"
    assert prova.mcp() == "2.3.0" and prova.extra_var()
    assert prova.systemctl() == ["--user stop ted-mcp", "--user reset-failed ted-mcp", "--user start ted-mcp"]
    assert f"main={prova.dal} dal ucu={prova.dal}" in r.stdout and "TAMAM" in r.stdout


def test_s2_baska_oturumun_commiti_onceden_maindeyse_hicbir_sey_yapilmaz(prova):
    prova.git("commit", "-q", "--allow-empty", "-m", "baska oturum")
    onceki = prova.rev("HEAD")
    r = prova.kos()
    assert r.returncode == 1 and "DUR (değişiklik yok)" in r.stdout
    assert prova.rev("HEAD") == onceki and prova.mesajlar()[0] == "baska oturum"
    assert prova.systemctl() == [] and prova.mcp() == "1.28.1"


def test_s3_izlenen_dosyada_kaydedilmemis_degisiklik_varsa_hicbir_sey_yapilmaz(prova):
    (prova.depo / "a.txt").write_text("başka oturumun yarım işi\n", encoding="utf-8")
    r = prova.kos()
    assert r.returncode == 1
    assert (prova.depo / "a.txt").read_text(encoding="utf-8") == "başka oturumun yarım işi\n"
    assert prova.systemctl() == []


def test_s4_dry_run_beklenmeyen_paket_gosterirse_hicbir_sey_yapilmaz(prova):
    r = prova.kos(STUB_DRY_RUN="mcp-2.3.0 mcp-types-2.3.0 opentelemetry-api-1.45.1 starlette-9.9.9")
    assert r.returncode == 1 and "dry-run beklenmeyen" in r.stdout
    assert prova.systemctl() == [] and prova.rev("main") == prova.taban


# -- s5: checkout değişirse başka dal ileri sarılmaz ---------------------------------------------------------

def test_s5_durdururken_checkout_ayni_committeki_baska_dala_gecerse_o_dal_ileri_sarilmaz(prova):
    """İnceleme bulgusu s5: merge --ff-only başka dalı ileri sarıyor, betik çıkış 0 ile 'TAMAM' diyordu."""
    r = prova.kos(STUB_STOP_HOOK=f"git -C {prova.depo} checkout -q -b baska {prova.taban}")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "TAMAM" not in r.stdout and "checkout değişmiş" in r.stdout
    assert prova.dal_adi() == "baska"
    assert prova.rev("baska") == prova.taban and prova.rev("main") == prova.taban
    assert prova.mcp() == "1.28.1"
    assert prova.systemctl()[-1] == "--user start ted-mcp"   # HEAD önceki main: bilinen kod


def test_s5b_checkout_bilinmeyen_koda_gecerse_hicbir_dala_dokunmaz_servisi_baslatmaz(prova):
    hook = (f"git -C {prova.depo} checkout -q -b baska {prova.taban} && "
            f"git -C {prova.depo} commit -q --allow-empty -m 'baska dal isi'")
    r = prova.kos(STUB_STOP_HOOK=hook)
    assert r.returncode == 3, r.stdout + r.stderr
    assert prova.mesajlar("baska")[0] == "baska dal isi" and prova.rev("main") == prova.taban
    assert "--user start ted-mcp" not in prova.systemctl()


def test_s5c_durdururken_maine_baska_commit_girerse_birlestirilmez_hicbir_sey_silinmez(prova):
    """İkinci inceleme bulgusu: korumasız 'git reset --keep $ONCEKI' burada başka oturumun commit'ini siliyordu."""
    r = prova.kos(STUB_STOP_HOOK=prova.baska_oturum_commit_komutu("durdurma sirasinda baska oturum"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.mesajlar()[:2] == ["durdurma sirasinda baska oturum", "taban"]
    assert "checkout değişmiş" in r.stdout and "birleştirme main'e girmemiş" in r.stdout
    assert prova.mcp() == "1.28.1" and not prova.extra_var()
    assert prova.systemctl()[-2:] == ["--user reset-failed ted-mcp", "--user start ted-mcp"]


def test_s5d_merge_ff_only_duserse_geri_doner_hicbir_sey_silinmez(prova):
    (prova.stub / "merge_duser").touch()
    r = prova.kos()
    assert r.returncode == 2, r.stdout + r.stderr
    assert "merge --ff-only düştü" in r.stdout
    assert prova.rev("main") == prova.taban and prova.rev("mcp-sdk-2") == prova.dal


# -- s6: sinyal ---------------------------------------------------------------------------------------------

def test_s6_kurulum_sirasinda_sinyal_gelirse_tek_girisli_geri_donus(prova):
    r = prova.kos(STUB_PIP_SINYAL="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stdout.count("GERİ DÖNÜŞ:") == 1 and "sinyal alındı" in r.stdout
    assert prova.rev("main") == prova.taban
    assert prova.mcp() == "1.28.1" and not prova.extra_var()
    assert prova.systemctl()[-1] == "--user start ted-mcp"


# -- s7–s8: stop düşerse --------------------------------------------------------------------------------------

def test_s7_stop_duser_servis_calisiyorsa_degisiklik_yok(prova):
    r = prova.kos(STUB_STOP_DUSER="1", STUB_IS_ACTIVE="active")
    assert r.returncode == 1 and "hâlâ çalışıyor" in r.stdout
    assert prova.systemctl() == ["--user stop ted-mcp", "--user is-active ted-mcp"]
    assert prova.rev("main") == prova.taban


def test_s8_stop_duser_servis_kapaliysa_eski_surumle_baslatir_ayri_cikis(prova):
    r = prova.kos(STUB_STOP_DUSER="1", STUB_IS_ACTIVE="failed")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "geçiş YAPILMADI" in r.stdout and "değişiklik yok" not in r.stdout
    assert prova.systemctl()[-2:] == ["--user reset-failed ted-mcp", "--user start ted-mcp"]
    assert prova.rev("main") == prova.taban and prova.mcp() == "1.28.1"


# -- s9: git hatası ----------------------------------------------------------------------------------------

def test_s9_merge_base_git_hatasi_elle_bak_cikisina_gider(prova):
    r = prova.kos(STUB_PIP_DUSER="1", STUB_PIP_HOOK=f"touch {prova.stub}/mb128")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "merge-base hata verdi" in r.stdout
    assert prova.rev("main") == prova.dal                   # dokunulmadı
    assert "--user start ted-mcp" not in prova.systemctl()


# -- s10: birleştirmenin üstüne başka commit ------------------------------------------------------------------

def test_s10_birlestirmenin_ustune_commit_geldiyse_revert_ile_geri_alir_kimseyi_silmez(prova):
    """KARAR (küçük 3): geri sarmak üstteki commit'i silerdi; commit'lerimiz git revert ile geri alınır, push yok."""
    r = prova.kos(STUB_PIP_DUSER="1", STUB_PIP_HOOK=prova.baska_oturum_commit_komutu("pip sirasinda baska oturum"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.mesajlar()[:4] == ['Revert "sdk 2.3.0"', "pip sirasinda baska oturum", "sdk 2.3.0", "taban"]
    assert not (prova.depo / "b.txt").exists()           # kodumuz geri alındı
    assert prova.git("status", "--porcelain") == ""
    assert prova.systemctl()[-1] == "--user start ted-mcp"
    assert "git revert ile geri alındı" in r.stdout


def test_s10b_revert_cakisirsa_iptal_eder_servisi_baslatmaz_riski_yazar(prova):
    hook = f"printf 'baska\\n' > {prova.depo}/b.txt && git -C {prova.depo} commit -q -am 'baska oturum b.txt'"
    r = prova.kos(STUB_PIP_DUSER="1", STUB_PIP_HOOK=hook)
    assert r.returncode == 3, r.stdout + r.stderr
    assert prova.mesajlar()[:3] == ["baska oturum b.txt", "sdk 2.3.0", "taban"]   # yarım revert yok
    assert prova.git("status", "--porcelain") == ""
    assert not (prova.depo / ".git" / "REVERT_HEAD").exists()
    assert "--user start ted-mcp" not in prova.systemctl()
    assert "RİSK: servis kapalı kalıyor" in r.stdout and "BAŞLATILMADI" in r.stdout


# -- s11–s15: paket ve açılış yolları --------------------------------------------------------------------------

def test_s11_pip_duserse_yalniz_kendi_birlestirmesini_geri_sarar_ve_eski_kodla_baslatir(prova):
    r = prova.kos(STUB_PIP_DUSER="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.rev("main") == prova.taban
    assert prova.rev("mcp-sdk-2") == prova.dal          # dal yerinde, iş kaybı yok
    assert prova.mcp() == "1.28.1"
    assert prova.systemctl()[-1] == "--user start ted-mcp"


def test_s12_acilista_cokerse_reset_failed_ile_eski_surume_doner(prova):
    r = prova.kos(STUB_2X_COKER="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert prova.rev("main") == prova.taban
    assert prova.mcp() == "1.28.1" and not prova.extra_var()
    calls = prova.systemctl()
    assert calls.count("--user reset-failed ted-mcp") == 2 and calls[-1] == "--user start ted-mcp"
    assert "ModuleNotFoundError" in (prova.kayit / "journal.txt").read_text(encoding="utf-8")


def test_s13_pip_check_tabana_gore_bozulursa_geri_doner(prova):
    r = prova.kos(STUB_CHECK_BOZUK="1")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "pip check bozuldu" in r.stdout
    assert prova.rev("main") == prova.taban and prova.mcp() == "1.28.1"
    assert (prova.kayit / "pip-check-oncesi.txt").read_text(encoding="utf-8").startswith("No broken")


def test_s14_tekerlek_gomulu_ozetle_tutmazsa_hicbir_sey_yapilmaz(prova):
    (prova.tek / "mcp-2.3.0-py3-none-any.whl").write_bytes(b"kurcalanmis")
    (prova.tek / "SHA256SUMS").write_text("dizindeki liste de kurcalanmış olabilir; betik ona bakmaz\n")
    r = prova.kos()
    assert r.returncode == 1 and "gömülü özetlerle tutmuyor" in r.stdout
    assert prova.systemctl() == []


def test_s15_dizinde_listede_olmayan_tekerlek_varsa_kurulum_reddedilir(prova):
    (prova.tek / "starlette-9.9.9-py3-none-any.whl").write_bytes(b"x")
    r = prova.kos()
    assert r.returncode == 1 and "beklenen dört dosyadan ibaret değil" in r.stdout
    assert prova.systemctl() == []
