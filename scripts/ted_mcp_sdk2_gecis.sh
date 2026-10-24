#!/usr/bin/env bash
# ted-mcp geçişinin 1. aşaması: mcp 1.28.1 → 2.3.0. TED_MCP_PROTOKOL_2026 varsayılanı 0 olduğundan birim ve .env
# değişmez. Paketler ağsız kurulur, önceden indirilmiş tekerleklerden. Kullanıcı onayıyla, birleştirmeden ÖNCE,
# çalışma ağacındaki kopyadan ve terminal kopsa da yarım kalmasın diye ayrı bir systemd birimi olarak koşulur:
#
#   systemd-run --user --wait --collect --unit=ted-mcp-gecis \
#     bash /mnt/thunderbolt/workspaces/TED/.claude/worktrees/mcp-sdk-2/scripts/ted_mcp_sdk2_gecis.sh
#   # izlemek için ikinci terminalde: journalctl --user -u ted-mcp-gecis -f
#
# Sıra: ön koşullar (hiçbiri değişiklik yapmaz) → stop → (checkout hâlâ main ve önceki HEAD mi?) → merge --ff-only
# <kayıtlı dal ucu> → pip (ağsız) → pip check (tabana göre) → reset-failed + start → /health → main doğrulaması.
# Herhangi bir adım ya da INT/TERM/HUP sinyali tek girişli geri dönüşü başlatır. main'e yalnız checkout main iken
# dokunulur: commit'lerimiz main'in ucuysa `git reset --keep`, üstüne başka commit geldiyse `git revert` (yeni commit
# ekler, kimsenin işini silmez, push yok). Başka bir oturumun commit'i ya da dalı asla geri sarılmaz.
#
# Çıkış kodları:
#   0  geçiş tamam
#   1  ön koşul tutmadı ya da servis durdurulamadı ve hâlâ eski sürümle çalışıyor; hiçbir şey değişmedi
#   2  geçiş düştü, geri dönüldü, servis 1.28.1 koduyla ayakta
#   3  otomatik geri dönüş tamamlanamadı ya da servis açılmadı (servis kapalı olabilir) — kayıt dizinine bak
#   4  stop düştü, servis kapalı bulundu ve geçişsiz, eski sürümle yeniden başlatıldı
#
# Değişkenler provada (tests/test_ted_mcp_gecis_betigi.py) sahte depo ve sahte systemctl/pip/curl içindir.
# Tekerleklerin özetleri betiğe gömülüdür; değiştirilemez.
set -u -o pipefail

KOK=${TED_KOK:-/mnt/thunderbolt/workspaces/TED}
DAL=${GECIS_DALI:-mcp-sdk-2}
TABAN=${BEKLENEN_TABAN:-e1ceaf6}
TEK=${TEKERLEKLER:-/home/mahirkurt/tekerlekler/ted-mcp-2026-10}
PY=${TED_PY:-$KOK/.venv/bin/python}
SYSTEMCTL=${SYSTEMCTL:-systemctl}
JOURNALCTL=${JOURNALCTL:-journalctl}
CURL=${CURL:-curl}
SAGLIK_URL=${SAGLIK_URL:-http://127.0.0.1:8090/health}
SAGLIK_SURE=${SAGLIK_SURE:-30}
KAYIT=${GECIS_KAYDI:-$HOME/ted-mcp-gecis-$(date +%Y%m%d-%H%M%S)}
YENI_PAKETLER=(mcp==2.3.0 mcp-types==2.3.0 opentelemetry-api==1.45.1)
BEKLENEN_KURULUM="mcp-2.3.0 mcp-types-2.3.0 opentelemetry-api-1.45.1"
# PyPI'dan 2026-10-24'te indirilen dört tekerlek. Dizinde bunlardan başka kurulabilir dosya olamaz.
BEKLENEN_OZETLER='2726bca5e7193f61c5dde8b12500a6de2d9acf6d1a1c0be9e8c2e706437991df  mcp-1.28.1-py3-none-any.whl
dd0c44c089d16453e8ae31a3877a0054d7a2314caaa81f5e0541b9b1734b2377  mcp-2.3.0-py3-none-any.whl
968efdbdaedfab06adae40d378a34395f1090c5921d4be3c9cde283aaf76d91d  mcp_types-2.3.0-py3-none-any.whl
b31553efa588ae44bc306f863c785c5333a9ecc091248c6ee68b4b6c87fdedfb  opentelemetry_api-1.45.1-py3-none-any.whl'

mkdir -p "$KAYIT" || exit 1
log() { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$KAYIT/gunluk.txt"; }
dur() { log "DUR (değişiklik yok): $*"; exit 1; }

# A, B'nin atası mı: 0 evet, 1 hayır, 2 git hata verdi (merge-base 128 vb.; "elle bak").
atasi_mi() {
  git merge-base --is-ancestor "$1" "$2" 2>>"$KAYIT/gunluk.txt"
  case $? in 0) return 0 ;; 1) return 1 ;; *) return 2 ;; esac
}

tekerlekleri_denetle() {
  printf '%s\n' "$BEKLENEN_OZETLER" >"$KAYIT/beklenen-ozetler.txt"
  local var bek
  var=$(cd "$TEK" && find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%f\n' | sort | xargs)
  bek=$(awk '{print $2}' "$KAYIT/beklenen-ozetler.txt" | sort | xargs)
  if [ "$var" != "$bek" ]; then
    log "tekerlek dizini beklenen dört dosyadan ibaret değil: '$var'"; return 1
  fi
  (cd "$TEK" && sha256sum -c --quiet "$KAYIT/beklenen-ozetler.txt") >>"$KAYIT/gunluk.txt" 2>&1
}

saglikli() {
  local i
  for i in $(seq 1 "$SAGLIK_SURE"); do
    "$CURL" -sf "$SAGLIK_URL" 2>/dev/null | grep -q '"status": *"ok"' && return 0
    sleep 1
  done
  return 1
}

baslat() {
  # StartLimitBurst=5 / 120 sn: önceki çökmeler sınırı doldurduysa start reddedilir; önce sayaç sıfırlanır.
  "$SYSTEMCTL" --user reset-failed ted-mcp >/dev/null 2>&1 || true
  "$SYSTEMCTL" --user start ted-mcp || return 1
  saglikli
}

geri_sar() {
  local main_sha dal
  main_sha=$(git rev-parse --verify --quiet refs/heads/main) || { log "main okunamadı; elle bakılmalı"; return 1; }
  atasi_mi "$DAL_UCU" "$main_sha"
  case $? in
    1) log "birleştirme main'e girmemiş (main $main_sha); main'e dokunulmadı"; return 0 ;;
    2) log "git merge-base hata verdi; main'e dokunulmadı, elle bakılmalı"; return 1 ;;
  esac
  dal=$(git branch --show-current)
  if [ "$dal" != main ]; then
    log "commit'lerimiz main'de ama checkout '$dal' dalında; hiçbir dala dokunulmadı, elle bakılmalı"; return 1
  fi
  if [ "$main_sha" = "$DAL_UCU" ]; then
    # Birleştirme oldu ve üstüne kimse yazmadı: yalnız o zaman geri sar. --keep: kaydedilmemiş iş korunur.
    git reset --keep "$ONCEKI" >>"$KAYIT/gunluk.txt" 2>&1 && { log "main geri sarıldı: $DAL_UCU → $ONCEKI"; return 0; }
    log "git reset --keep başarısız; elle bakılmalı"; return 1
  fi
  # Üstüne başka commit gelmiş: geri sarmak onu silerdi. Geri alma commit'leri eklenir (push yok).
  if git revert --no-edit "$ONCEKI..$DAL_UCU" >>"$KAYIT/gunluk.txt" 2>&1; then
    log "üstüne başka commit gelmiş; commit'lerimiz git revert ile geri alındı ($ONCEKI..$DAL_UCU, push yok)"; return 0
  fi
  if git rev-parse --verify --quiet REVERT_HEAD >/dev/null || [ -d "$(git rev-parse --git-dir)/sequencer" ]; then
    git revert --abort >>"$KAYIT/gunluk.txt" 2>&1
  fi
  log "git revert çakıştı ya da düştü; iptal edildi (main $(git rev-parse HEAD)). RİSK: servis kapalı kalıyor."
  return 1
}

paket_geri() {
  "$PY" -m pip freeze >"$KAYIT/freeze-geri-oncesi.txt" 2>/dev/null
  if cmp -s "$KAYIT/freeze-oncesi.txt" "$KAYIT/freeze-geri-oncesi.txt"; then
    log "paketler değişmemiş; pip'e dokunulmadı"; return 0
  fi
  "$PY" -m pip install --no-index --find-links "$TEK" "mcp==1.28.1" >>"$KAYIT/pip.txt" 2>&1 || {
    log "mcp==1.28.1 kurulamadı"; return 1; }
  local p
  for p in mcp-types opentelemetry-api; do
    grep -qi "^$p==" "$KAYIT/freeze-oncesi.txt" || "$PY" -m pip uninstall -y "$p" >>"$KAYIT/pip.txt" 2>&1
  done
  "$PY" -m pip freeze >"$KAYIT/freeze-geri-sonrasi.txt" 2>/dev/null
  if cmp -s "$KAYIT/freeze-oncesi.txt" "$KAYIT/freeze-geri-sonrasi.txt"; then
    log "paketler geçiş öncesine döndü"; return 0
  fi
  log "paketler geçiş öncesine dönmedi:"; diff "$KAYIT/freeze-oncesi.txt" "$KAYIT/freeze-geri-sonrasi.txt" | tee -a "$KAYIT/gunluk.txt"
  return 1
}

GERI_DONUYOR=0
geri_don() {
  # Tek giriş: geri dönüş sırasında gelen sinyal ya da ikinci çağrı yeni bir geri dönüş başlatmaz.
  [ "$GERI_DONUYOR" = 1 ] && return 0
  GERI_DONUYOR=1
  trap '' INT TERM HUP
  log "GERİ DÖNÜŞ: $1"
  "$JOURNALCTL" --user -u ted-mcp -n 80 --no-pager >"$KAYIT/journal.txt" 2>&1 || true
  "$SYSTEMCTL" --user stop ted-mcp >/dev/null 2>&1 || true
  local kod=0 paket=0 dal bas
  geri_sar || kod=1
  paket_geri || paket=1
  if [ "$kod" -ne 0 ] || [ "$paket" -ne 0 ]; then
    log "Otomatik geri dönüş tamamlanamadı; servis BAŞLATILMADI (kod ile paket uyuşmayabilir)."
    log "Elle: kayıt dizini $KAYIT, rapor §7 'Sonradan elle geri dönüş' (dal ucu=$DAL_UCU)."
    exit 3
  fi
  dal=$(git branch --show-current); bas=$(git rev-parse HEAD)
  if [ "$dal" != main ] && [ "$bas" != "$ONCEKI" ]; then
    # Servis checkout'taki dosyalardan çalışır; başka bir dalın bilinmeyen kodunu biz başlatmayız.
    log "checkout '$dal' dalında ve HEAD ($bas) önceki main değil; servis BAŞLATILMADI, elle bakılmalı."
    exit 3
  fi
  if baslat; then
    log "ted-mcp 1.28.1 koduyla ayakta (checkout '$dal', HEAD $bas)."; exit 2
  fi
  log "Geri dönülen sürüm de açılmadı; journal: $KAYIT/journal.txt (journalctl --user -u ted-mcp -n 80)."
  exit 3
}

# --- 0. Ön koşullar: hiçbiri değişiklik yapmaz --------------------------------------------------------------
log "kayıt dizini: $KAYIT"
cd "$KOK" || dur "$KOK yok"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || dur "$KOK bir git deposu değil"
[ "$(git branch --show-current)" = main ] || dur "dal main değil: $(git branch --show-current)"
[ -z "$(git status --porcelain --untracked-files=no)" ] || dur "izlenen dosyalarda kaydedilmemiş değişiklik var"
ONCEKI=$(git rev-parse HEAD)
TABAN_SHA=$(git rev-parse --verify --quiet "$TABAN^{commit}") || dur "taban commit yok: $TABAN"
[ "$ONCEKI" = "$TABAN_SHA" ] || dur "main $TABAN değil ($ONCEKI). Dal önce main'e rebase edilip testler yeniden koşulmalı."
DAL_UCU=$(git rev-parse --verify --quiet "$DAL^{commit}") || dur "dal yok: $DAL"
[ "$ONCEKI" != "$DAL_UCU" ] || dur "$DAL zaten main'de"
atasi_mi "$ONCEKI" "$DAL_UCU" || dur "$DAL, main'in üstünde değil (ff olamaz) ya da git hata verdi"
log "main=$ONCEKI dal ucu=$DAL_UCU"
tekerlekleri_denetle || dur "tekerlekler gömülü özetlerle tutmuyor: $TEK"
[ -x "$PY" ] || dur "python yok: $PY"
"$PY" -m pip freeze >"$KAYIT/freeze-oncesi.txt" 2>/dev/null || dur "pip freeze koşmadı"
grep -qx "mcp==1.28.1" "$KAYIT/freeze-oncesi.txt" || dur "kurulu mcp 1.28.1 değil: $(grep -i '^mcp==' "$KAYIT/freeze-oncesi.txt")"
"$PY" -m pip check >"$KAYIT/pip-check-oncesi.txt" 2>&1
PIP_CHECK_TABAN=$?
log "pip check tabanı: rc=$PIP_CHECK_TABAN"
"$PY" -m pip install --dry-run --no-index --find-links "$TEK" "${YENI_PAKETLER[@]}" >"$KAYIT/dry-run.txt" 2>&1 \
  || dur "pip --dry-run düştü (bkz. $KAYIT/dry-run.txt)"
KURULACAK=$(grep '^Would install ' "$KAYIT/dry-run.txt" | sed 's/^Would install //' | tr ' ' '\n' | sort | xargs)
BEKLENEN=$(printf '%s\n' $BEKLENEN_KURULUM | sort | xargs)
[ "$KURULACAK" = "$BEKLENEN" ] || dur "dry-run beklenmeyen kurulum gösteriyor: '$KURULACAK' (beklenen '$BEKLENEN')"
log "dry-run: $KURULACAK"

# --- 1. Durdur ----------------------------------------------------------------------------------------------
# Sinyal tuzağı stop'tan hemen önce: stop sürerken gelen bir sinyal de geri dönüşe (yani yeniden başlatmaya) gider.
trap 'geri_don "sinyal alındı"' INT TERM HUP
if ! "$SYSTEMCTL" --user stop ted-mcp; then
  trap - INT TERM HUP
  DURUM=$("$SYSTEMCTL" --user is-active ted-mcp 2>/dev/null)
  [ "$DURUM" = active ] && dur "ted-mcp durdurulamadı ve hâlâ çalışıyor (eski sürüm)"
  log "stop düştü ve servis '$DURUM'; geçiş YAPILMADI, eski sürümle yeniden başlatılıyor"
  if baslat; then log "ted-mcp eski sürümle ayakta; geçiş yapılmadı."; exit 4; fi
  log "ted-mcp açılamadı; servis kapalı, elle bakılmalı (journalctl --user -u ted-mcp -n 80)."; exit 3
fi
log "ted-mcp durduruldu"

# --- 2. Birleştir (yalnız checkout hâlâ main ve önceki HEAD iken; kayıtlı dal ucuyla) ----------------------------
if ! { [ "$(git branch --show-current)" = main ] && [ "$(git rev-parse HEAD)" = "$ONCEKI" ]; }; then
  geri_don "durdurma sırasında checkout değişmiş (dal '$(git branch --show-current)', HEAD $(git rev-parse HEAD)); birleştirme yapılmadı"
fi
if ! git merge --ff-only "$DAL_UCU" >>"$KAYIT/gunluk.txt" 2>&1; then
  geri_don "merge --ff-only düştü"
fi
log "main ileri sarıldı: $ONCEKI → $(git rev-parse refs/heads/main)"

# --- 3. Paketler (ağsız) ------------------------------------------------------------------------------------
if ! "$PY" -m pip install --no-index --find-links "$TEK" "${YENI_PAKETLER[@]}" >>"$KAYIT/pip.txt" 2>&1; then
  geri_don "pip install düştü (bkz. $KAYIT/pip.txt)"
fi
"$PY" -m pip check >"$KAYIT/pip-check-sonrasi.txt" 2>&1
PIP_CHECK_SONRA=$?
if [ "$PIP_CHECK_TABAN" -eq 0 ] && [ "$PIP_CHECK_SONRA" -ne 0 ]; then
  geri_don "pip check bozuldu (taban temizdi; bkz. $KAYIT/pip-check-sonrasi.txt)"
fi
if [ "$PIP_CHECK_TABAN" -ne 0 ] && grep -vxF -f "$KAYIT/pip-check-oncesi.txt" "$KAYIT/pip-check-sonrasi.txt" >"$KAYIT/pip-check-yeni.txt"; then
  geri_don "pip check'te tabanda olmayan yeni satırlar var (bkz. $KAYIT/pip-check-yeni.txt)"
fi
"$PY" -m pip freeze >"$KAYIT/freeze-sonrasi.txt" 2>/dev/null
log "paketler kuruldu; pip check rc=$PIP_CHECK_SONRA (taban $PIP_CHECK_TABAN)"

# --- 4. Başlat ve sağlık ------------------------------------------------------------------------------------
# Servis checkout'taki dosyalardan çalışır: başlatmadan önce checkout main ve commit'lerimizi içeriyor olmalı.
[ "$(git branch --show-current)" = main ] && atasi_mi "$DAL_UCU" HEAD \
  || geri_don "başlatmadan önce checkout main değil ya da dal ucunu içermiyor"
if ! baslat; then
  geri_don "ted-mcp 2.3.0 ile açılmadı ya da /health $SAGLIK_SURE sn içinde 'ok' demedi"
fi
MAIN_SON=$(git rev-parse refs/heads/main)
atasi_mi "$DAL_UCU" "$MAIN_SON" || geri_don "main ($MAIN_SON) dal ucunu ($DAL_UCU) içermiyor"
trap - INT TERM HUP
log "TAMAM: ted-mcp mcp 2.3.0 ile ayakta (TED_MCP_PROTOKOL_2026 varsayılan 0); main=$MAIN_SON dal ucu=$DAL_UCU"
diff "$KAYIT/freeze-oncesi.txt" "$KAYIT/freeze-sonrasi.txt" | tee -a "$KAYIT/gunluk.txt"
exit 0
