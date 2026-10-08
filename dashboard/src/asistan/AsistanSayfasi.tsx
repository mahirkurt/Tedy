import './AsistanSayfasi.scss'
import { useEffect, useRef, type CSSProperties } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChatCustomElement } from '@carbon/ai-chat'
import OgretmenSecici from '../components/OgretmenSecici'
import { subjectClass } from '../utils/subject'
import { useAsistanSohbeti } from './useAsistanSohbeti.tsx'
import { kaydirmaOdaginiYonet } from './kaydirmaOdagi.ts'
import { VOICE } from './ses.ts'
import { useAsistanDurumu } from './asistanDeposu.ts'
import SesOnayi from './SesOnayi.tsx'
import { ogretmenDegiskenleri } from './ogretmenRenkleri.ts'
import { dosyalariEkle } from './ekler.ts'
import { carbonErisilebilirlikOnarimi } from './carbonOnarimi.ts'
import { sayfaEtiketi } from './sayfaBaglami.ts'

export default function AsistanSayfasi() {
  // Telefonda alt gezinmenin Asistan sekmesi bulunulan sayfayı taşır (?sayfa=isler); bilinmeyen ad yok sayılır.
  const [arama] = useSearchParams()
  const istenen = arama.get('sayfa')
  const { props, hazir, ogretmen, ogretmenSec, sesOnay } = useAsistanSohbeti('sayfa', sayfaEtiketi(istenen) ? istenen : null)
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
  const okur = useAsistanDurumu(d => d.okur)
  return (
    <section ref={kok} className={['asistan', secili && subjectClass(null, secili.renk_ailesi)].filter(Boolean).join(' ')}
      data-ogretmen={ogretmen.id}>
      <OgretmenSecici liste={ogretmen.liste} secili={ogretmen.id} onSec={id => void ogretmenSec(id)}
        hata={ogretmen.hata ? VOICE[okur].ogretmenHata : null} />
      {/* KaTeX yüklemesi sonuçlanınca (başarılı ya da değil) çizilir; markdownKurulumu.ts. */}
      {hazir && <ChatCustomElement className="asistan__sohbet" {...props}
        style={ogretmenDegiskenleri(secili?.renk_ailesi ?? null) as CSSProperties} />}
      <SesOnayi onay={sesOnay} />
    </section>
  )
}
