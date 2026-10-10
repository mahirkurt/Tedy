import { Modal } from '@carbon/react'
import { useAsistanDurumu } from './asistanDeposu.ts'

/** Öğrenciye aile notu, ses hatası ve ilk mikrofon kullanımının onayı. Pencerenin başlığı ve birincil düğmesi
 *  tetikle aynı fiili taşır ("Mikrofonu aç", B41). */
export default function SesOnayi({ onay }: { onay: { acik: boolean; onayla: () => void; vazgec: () => void; hata: string | null } }) {
  const ogrenci = useAsistanDurumu(d => d.okur === 'ogrenci')
  return <>
    {ogrenci && <p className="asistan__aile-notu">Sohbetlerini ailen de görebilir.</p>}
    {onay.hata && <p role="alert" className="asistan__ses-hata">{onay.hata}</p>}
    <Modal open={onay.acik} size="xs" modalHeading="Mikrofonu açalım mı?" primaryButtonText="Mikrofonu aç" secondaryButtonText="Vazgeç"
      onRequestSubmit={onay.onayla} onRequestClose={onay.vazgec} onSecondarySubmit={onay.vazgec}>
      <p>Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.</p>
    </Modal>
  </>
}
