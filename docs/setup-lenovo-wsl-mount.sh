#!/bin/bash
# =============================================================================
# Lenovo PC2 WSL Ubuntu'da /mnt/thunderbolt kalıcı mount yapılandırması
# Bu scripti Lenovo PC2'deki WSL Ubuntu terminalinde root olarak çalıştırın:
#   sudo bash setup-lenovo-wsl-mount.sh
# =============================================================================
set -e

SHARE_HOST="100.107.62.43"          # hp-ai-node Tailscale IP
SHARE_NAME="thunderbolt"
MOUNT_POINT="/mnt/thunderbolt"
SMB_USER="mahirkurt"
CRED_FILE="/root/.smbcredentials_hp"

echo "=== Lenovo WSL: /mnt/thunderbolt Samba Mount Kurulumu ==="

# 1. Gerekli paketleri kur
echo "[1/5] cifs-utils kurulumu..."
apt-get update -qq && apt-get install -y -qq cifs-utils > /dev/null 2>&1
echo "      cifs-utils kuruldu."

# 2. Mount noktasını oluştur
echo "[2/5] Mount noktası oluşturuluyor: ${MOUNT_POINT}"
mkdir -p "${MOUNT_POINT}"

# 3. Kimlik bilgileri dosyası oluştur
echo "[3/5] Samba kimlik bilgileri dosyası oluşturuluyor..."
if [[ -f "${CRED_FILE}" ]]; then
    echo "      ${CRED_FILE} zaten var, atlanıyor."
else
    read -sp "Samba şifresi (mahirkurt@hp-ai-node): " SMB_PASS
    echo
    cat > "${CRED_FILE}" << CREDEOF
username=${SMB_USER}
password=${SMB_PASS}
CREDEOF
    chmod 600 "${CRED_FILE}"
    echo "      Kimlik bilgileri ${CRED_FILE} dosyasına kaydedildi (mod 600)."
fi

# 4. /etc/fstab'a kalıcı mount girişi ekle
echo "[4/5] /etc/fstab yapılandırılıyor..."
FSTAB_ENTRY="//${SHARE_HOST}/${SHARE_NAME}  ${MOUNT_POINT}  cifs  credentials=${CRED_FILE},uid=0,gid=0,file_mode=0775,dir_mode=0775,vers=3.0,nofail,x-systemd.automount,x-systemd.device-timeout=10  0  0"

if grep -qF "${SHARE_HOST}/${SHARE_NAME}" /etc/fstab 2>/dev/null; then
    echo "      fstab girişi zaten var, atlanıyor."
else
    echo "" >> /etc/fstab
    echo "# HP AI-Node Thunderbolt SSD (Samba over Tailscale)" >> /etc/fstab
    echo "${FSTAB_ENTRY}" >> /etc/fstab
    echo "      fstab girişi eklendi."
fi

# 5. Şimdi mount et
echo "[5/5] Mount ediliyor..."
mount -a 2>/dev/null || mount "${MOUNT_POINT}" 2>/dev/null || true

if mountpoint -q "${MOUNT_POINT}"; then
    echo ""
    echo "=== BAŞARILI ==="
    echo "/mnt/thunderbolt başarıyla mount edildi!"
    echo "Doğrulama:"
    ls -la "${MOUNT_POINT}" | head -10
    echo ""
    echo "Windows'tan erişim: \\\\wsl.localhost\\Ubuntu\\mnt\\thunderbolt"
else
    echo ""
    echo "=== UYARI ==="
    echo "Otomatik mount başarısız oldu. Manuel olarak deneyin:"
    echo "  sudo mount -t cifs //${SHARE_HOST}/${SHARE_NAME} ${MOUNT_POINT} -o credentials=${CRED_FILE},vers=3.0"
    echo ""
    echo "Tailscale bağlantısını kontrol edin:"
    echo "  ping ${SHARE_HOST}"
fi

echo ""
echo "=== WSL Başlangıcında Otomatik Mount ==="
echo "WSL her açıldığında otomatik mount için /etc/wsl.conf dosyasına ekleyin:"
echo ""
echo "[boot]"
echo "command = mount -a"
echo ""
