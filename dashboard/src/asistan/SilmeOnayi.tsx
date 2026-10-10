import { useState } from 'react'
import { Modal } from '@carbon/react'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'

/**
 * Geri dönüşsüz silmenin onayı (S40, B23): Carbon tehlike modalı; başlık ve birincil düğme nesneyi adlandırır,
 * gövde birlikte gidenleri sayar, ilk odak "Vazgeç"tedir. Sohbet kabının (gölge kök) dışında çizilir: Carbon'un
 * paneli dönüşüm taşıyabilir ve sabit konumlu modal onun içinde kırpılırdı.
 */
export default function SilmeOnayi() {
  const istek = useAsistanDurumu(d => d.silinecek)
  const [siliniyor, setSiliniyor] = useState(false)
  const kapat = () => { if (!siliniyor) asistanDeposu.ayarla({ silinecek: null }) }
  async function sil() {
    if (!istek || siliniyor) return
    setSiliniyor(true)
    try { await istek.sil() } catch { istek.hataBildir(istek.hata) } finally {
      setSiliniyor(false)
      asistanDeposu.ayarla({ silinecek: null })
    }
  }
  return <Modal open={!!istek} danger size="xs" closeButtonLabel="Kapat" modalHeading={istek?.baslik ?? ''} primaryButtonText={istek?.dugme ?? 'Sil'}
    secondaryButtonText="Vazgeç" selectorPrimaryFocus=".cds--btn--secondary" primaryButtonDisabled={siliniyor}
    loadingStatus={siliniyor ? 'active' : 'inactive'} loadingDescription="Siliniyor…"
    onRequestSubmit={() => void sil()} onRequestClose={kapat} onSecondarySubmit={kapat}>
    <p>{istek?.govde}</p>
  </Modal>
}
