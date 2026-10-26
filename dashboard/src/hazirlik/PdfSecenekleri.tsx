import { useState } from 'react'
import { Checkbox, InlineNotification, Modal } from '@carbon/react'
import { useSession } from '../contexts/session'
import { pdfAdresi } from './hazirlik'
import { pdfIndir } from './pdfIndir'
import { pdfSecenekleriniKaydet, usePdfSecenekleri } from './usePdfSecenekleri'

/** PDF seçenekleri penceresi (spec §4): ebeveyn özeti ve hazırlık işaretleri; son seçim bu cihazda kişi başına
 *  hatırlanır (D26). YZ ve prova seçenekleri Plan 2'dedir ve burada yoktur (yapılamayan eylem gizlenir, B42). Yalnız
 *  açıkken bağlanır: her açılışta kayıtlı seçimle başlar; kapanınca odağı açan düğmeye çağıran döndürür. */
export default function PdfSecenekleri({ anahtar, no, senaryo, kapat }: {
  anahtar: string; no: number; senaryo: number | null; kapat: () => void
}) {
  const email = useSession()?.email ?? ''
  const kayitli = usePdfSecenekleri(email)
  const [s, setS] = useState(kayitli)
  const [hazirlaniyor, setHazirlaniyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)
  const indir = async () => {
    pdfSecenekleriniKaydet(email, s)
    setHazirlaniyor(true)
    setHata(null)
    const sonuc = await pdfIndir(pdfAdresi(anahtar, no, senaryo, s))
    setHazirlaniyor(false)
    if (sonuc === null) kapat()
    else setHata(sonuc)
  }
  const vazgec = () => { if (!hazirlaniyor) kapat() }
  return (
    <Modal open size="sm" modalHeading="Kılavuzu PDF olarak indir" closeButtonLabel="Kapat"
      primaryButtonText="PDF'i indir" secondaryButtonText="Vazgeç"
      loadingStatus={hazirlaniyor ? 'active' : 'inactive'} loadingDescription="PDF hazırlanıyor…"
      loadingIconDescription="Hazırlanıyor" onRequestClose={vazgec}
      onRequestSubmit={() => { if (!hazirlaniyor) void indir() }}>
      <p className="hazirlik-pdf__not">Seçimin bu cihazda hatırlanır.</p>
      <Checkbox id="pdf-ebeveyn" labelText="Ebeveyn özetini başa ekle" checked={s.ebeveyn}
        onChange={(_, { checked }) => setS({ ...s, ebeveyn: checked })} />
      <Checkbox id="pdf-isaret" labelText="Hazırlık işaretlerimi ekle" checked={s.isaret}
        onChange={(_, { checked }) => setS({ ...s, isaret: checked })} />
      {hata && <InlineNotification kind="error" lowContrast hideCloseButton role="alert" statusIconDescription="Hata"
        title={hata} className="hazirlik-pdf__hata" />}
    </Modal>
  )
}
