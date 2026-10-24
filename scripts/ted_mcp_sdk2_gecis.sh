#!/usr/bin/env bash
# ted-mcp geçişinin 1. aşaması: mcp 1.28.1 → 2.3.0. TED_MCP_PROTOKOL_2026 varsayılanı 0 olduğundan birim ve .env
# değişmez. Paketler ağsız kurulur, önceden indirilmiş tekerleklerden. Kullanıcı onayıyla, elle, birleştirmeden ÖNCE
# çalışma ağacındaki kopyadan koşulur:
#
#   bash /mnt/thunderbolt/workspaces/TED/.claude/worktrees/mcp-sdk-2/scripts/ted_mcp_sdk2_gecis.sh
#
# Sıra: ön koşullar (hiçbiri değişiklik yapmaz) → stop → merge --ff-only → pip (ağsız) → pip check (tabana göre)
# → reset-failed + start → /health. Herhangi bir adım düşerse betik kendisi geri döner. main yalnız birleştirme
# gerçekten olduysa (HEAD = dal ucu) geri sarılır; başka bir oturumun commit'ine asla dokunmaz.
#
# Çıkış kodları:
#   0  geçiş tamam
#   1  ön koşul tutmadı, hiçbir şey değişmedi
#   2  geçiş düştü, geri dönüldü, servis 1.28.1 ile ayakta
#   3  otomatik geri dönüş tamamlanamadı (servis başlatılmadı ya da açılmadı) — kayıt dizinine bak
#
# Değişkenler, provada (tests/test_ted_mcp_gecis_betigi.py) sahte depo ve sahte systemctl/pip/curl içindir.
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

mkdir -p "$KAYIT" || exit 1
log() { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$KAYIT/gunluk.txt"; }
dur() { log "DUR (değişiklik yok): $*"; exit 1; }

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
  local bas
  bas=$(git rev-parse HEAD)
  if [ "$bas" = "$DAL_UCU" ] && [ "$ONCEKI" != "$DAL_UCU" ]; then
    # Birleştirme gerçekten oldu ve üstüne kimse yazmadı: yalnız o zaman geri sar. --keep: kaydedilmemiş iş korunur.
    git reset --keep "$ONCEKI" && { log "main geri sarıldı: $DAL_UCU → $ONCEKI"; return 0; }
    log "git reset --keep başarısız"; return 1
  fi
  if ! git merge-base --is-ancestor "$DAL_UCU" "$bas"; then
    # Bizim commit'lerimiz main'e hiç girmedi (ör. ff-only, araya giren bir commit yüzünden düştü):
    # geri alınacak bir şey yok; main'deki her commit başkasınındır ve olduğu gibi kalır.
    log "birleştirme main'e girmemiş (HEAD $bas); main'e dokunulmadı"; return 0
  fi
  log "birleştirmenin üstüne başka commit gelmiş (HEAD $bas); main geri sarılmadı, elle bakılmalı."
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

geri_don() {
  log "GERİ DÖNÜŞ: $1"
  "$JOURNALCTL" --user -u ted-mcp -n 80 --no-pager >"$KAYIT/journal.txt" 2>&1 || true
  "$SYSTEMCTL" --user stop ted-mcp >/dev/null 2>&1 || true
  local kod=0 paket=0
  geri_sar || kod=1
  paket_geri || paket=1
  if [ "$kod" -ne 0 ] || [ "$paket" -ne 0 ]; then
    log "Otomatik geri dönüş tamamlanamadı; servis BAŞLATILMADI (kod ile paket uyuşmayabilir)."
    log "Elle: kayıt dizini $KAYIT, rapor §7 'Geri dönüş'."
    exit 3
  fi
  if baslat; then
    log "ted-mcp 1.28.1 koduyla ayakta."; exit 2
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
git merge-base --is-ancestor "$ONCEKI" "$DAL_UCU" || dur "$DAL, main'in üstünde değil (ff olamaz)"
log "main=$ONCEKI dal ucu=$DAL_UCU"
(cd "$TEK" && sha256sum -c --quiet SHA256SUMS) >>"$KAYIT/gunluk.txt" 2>&1 || dur "tekerlek özetleri tutmuyor: $TEK"
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
"$SYSTEMCTL" --user stop ted-mcp || dur "ted-mcp durdurulamadı"
log "ted-mcp durduruldu"

# --- 2. Birleştir (yalnız ileri sarma; kayıtlı dal ucu, hareket eden ad değil) ---------------------------------
if ! git merge --ff-only "$DAL_UCU" >>"$KAYIT/gunluk.txt" 2>&1; then
  geri_don "merge --ff-only düştü (main bu arada ilerlemiş olabilir)"
fi
log "main ileri sarıldı: $ONCEKI → $(git rev-parse HEAD)"

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
if ! baslat; then
  geri_don "ted-mcp 2.3.0 ile açılmadı ya da /health $SAGLIK_SURE sn içinde 'ok' demedi"
fi
log "TAMAM: ted-mcp mcp 2.3.0 ile ayakta (TED_MCP_PROTOKOL_2026 varsayılan 0). freeze farkı:"
diff "$KAYIT/freeze-oncesi.txt" "$KAYIT/freeze-sonrasi.txt" | tee -a "$KAYIT/gunluk.txt"
exit 0
