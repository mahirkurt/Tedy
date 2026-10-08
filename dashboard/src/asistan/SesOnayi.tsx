import { Modal } from '@carbon/react'
import { useAsistanDurumu } from './asistanDeposu.ts'

export default function SesOnayi({ onay }: { onay: { acik: boolean; onayla: () => void; vazgec: () => void; hata: string | null } }) {
  const ogrenci = useAsistanDurumu(d => d.okur === 'ogrenci')
  return <>
    {ogrenci && <p className="asistan__aile-notu">Sohbetlerini ailen de görebilir.</p>}
    {onay.hata && <p role="alert" className="ac__ses-hata">{onay.hata}</p>}
    <Modal open={onay.acik} modalHeading="Mikrofon" primaryButtonText="Onayla" secondaryButtonText="Vazgeç"
      onRequestSubmit={onay.onayla} onRequestClose={onay.vazgec} onSecondarySubmit={onay.vazgec}>
      <p>Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.</p>
    </Modal>
  </>
}
