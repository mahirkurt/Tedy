import './AsistanSayfasi.scss'
import { useEffect, useRef } from 'react'
import { ChatCustomElement } from '@carbon/ai-chat'
import OgretmenSecici from '../components/OgretmenSecici'
import { subjectClass } from '../utils/subject'
import { useAsistanSohbeti } from './useAsistanSohbeti.tsx'
import { kaydirmaOdaginiYonet } from './kaydirmaOdagi.ts'
import { VOICE } from './ses.ts'
import { useAsistanDurumu } from './asistanDeposu.ts'

export default function AsistanSayfasi() {
  const { props, ogretmen, ogretmenSec } = useAsistanSohbeti('sayfa')
  const kok = useRef<HTMLElement>(null)
  useEffect(() => (kok.current ? kaydirmaOdaginiYonet(kok.current) : undefined), [])
  const secili = ogretmen.secili
  const okur = useAsistanDurumu(d => d.okur)
  return (
    <section ref={kok} className={['asistan', secili && subjectClass(null, secili.renk_ailesi)].filter(Boolean).join(' ')}
      data-ogretmen={ogretmen.id}>
      <OgretmenSecici liste={ogretmen.liste} secili={ogretmen.id} onSec={id => void ogretmenSec(id)}
        hata={ogretmen.hata ? VOICE[okur].ogretmenHata : null} />
      {okur === 'ogrenci' && <p className="asistan__aile-notu">Sohbetlerini ailen de görebilir.</p>}
      <ChatCustomElement className="asistan__sohbet" {...props} />
    </section>
  )
}
