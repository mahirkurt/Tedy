import './Asistan.scss'
import './AsistanSayfasi.scss'
import { useEffect, useRef, type CSSProperties } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChatCustomElement } from '@carbon/ai-chat'
import { subjectClass } from '../utils/subject'
import { useAsistanSohbeti } from './useAsistanSohbeti.tsx'
import { kaydirmaOdaginiYonet } from './kaydirmaOdagi.ts'
import SesOnayi from './SesOnayi.tsx'
import SilmeOnayi from './SilmeOnayi.tsx'
import { ogretmenDegiskenleri } from './ogretmenRenkleri.ts'
import { dosyalariEkle } from './ekler.ts'
import { carbonErisilebilirlikOnarimi } from './carbonOnarimi.ts'
import { sayfaEtiketi } from './sayfaBaglami.ts'
import { useGecmisGenisligi } from './useDar.ts'

export default function AsistanSayfasi() {
  // Telefonda alt gezinmenin Asistan sekmesi bulunulan sayfayı taşır (?sayfa=isler); bilinmeyen ad yok sayılır.
  const [arama] = useSearchParams()
  const istenen = arama.get('sayfa')
  const { props, hazir, ogretmen, sesOnay } = useAsistanSohbeti('sayfa', sayfaEtiketi(istenen) ? istenen : null)
  const kok = useRef<HTMLElement>(null)
  useEffect(() => (kok.current ? kaydirmaOdaginiYonet(kok.current) : undefined), [])
  useEffect(() => (kok.current ? carbonErisilebilirlikOnarimi(kok.current) : undefined), [])
  // Sürükle-bırak ve dosya yapıştırma (eski giriş alanı gibi). Yakalama evresi: Carbon'un düzenleyicisi gölge
  // kökte işlemeden önce dosyalar alınır; düz metin yapıştırma dokunulmadan geçer.
  useEffect(() => {
    const el = kok.current
    if (!el) return
    // Dosya içeren olay düzenleyiciye hiç ulaşmaz: Carbon'un düzenleyicisi dosya yapıştırmasında yazılan metni siliyordu.
    const yapistir = (e: ClipboardEvent) => { const f = e.clipboardData?.files; if (f?.length) { e.preventDefault(); e.stopPropagation(); dosyalariEkle([...f]) } }
    const birak = (e: DragEvent) => { if (e.dataTransfer?.files.length) { e.preventDefault(); e.stopPropagation(); dosyalariEkle([...e.dataTransfer.files]) } }
    const uzerinde = (e: DragEvent) => e.preventDefault()
    el.addEventListener('paste', yapistir, true); el.addEventListener('drop', birak, true); el.addEventListener('dragover', uzerinde)
    return () => { el.removeEventListener('paste', yapistir, true); el.removeEventListener('drop', birak, true); el.removeEventListener('dragover', uzerinde) }
  }, [])
  const secili = ogretmen.secili
  // Geçmiş paneli 20rem (4K'da kökle büyür, B28'in genişlik kısmı); px olarak, bkz. useGecmisGenisligi.
  const gecmis = useGecmisGenisligi()
  return (
    <section ref={kok} className={['asistan', secili && subjectClass(null, secili.renk_ailesi)].filter(Boolean).join(' ')}
      data-ogretmen={ogretmen.id}>
      {/* KaTeX yüklemesi sonuçlanınca (başarılı, başarısız ya da süre dolunca) çizilir; markdownKurulumu.ts.
          Beklerken alan boş kalmaz (D3). */}
      {!hazir && <p className="app-shell-loading__text" role="status">Asistan yükleniyor…</p>}
      {hazir && <ChatCustomElement className="asistan__sohbet" {...props}
        style={{ ...ogretmenDegiskenleri(secili?.renk_ailesi ?? null), '--cds-aichat-history-width': gecmis } as CSSProperties} />}
      <SesOnayi onay={sesOnay} />
      <SilmeOnayi />
    </section>
  )
}
