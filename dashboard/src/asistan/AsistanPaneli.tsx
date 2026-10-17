import './Asistan.scss'
import './AsistanBaslatici.scss'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { useLocation } from 'react-router-dom'
import { ChatContainer } from '@carbon/ai-chat'
import { Maximize, Minimize } from '@carbon/icons-react'
import { useAsistanSohbeti } from './useAsistanSohbeti.tsx'
import { ogretmenDegiskenleri } from './ogretmenRenkleri.ts'
import { ASISTANA_SOR, sayfaAdi } from './sayfaBaglami.ts'
import { kaydirmaOdaginiYonet } from './kaydirmaOdagi.ts'
import { carbonErisilebilirlikOnarimi } from './carbonOnarimi.ts'
import SesOnayi from './SesOnayi.tsx'
import SilmeOnayi from './SilmeOnayi.tsx'
import { subjectClass } from '../utils/subject'
import { MESAJ_GENISLIGI } from './tedyChatConfig.ts'
import { useGecmisGenisligi } from './useDar.ts'

/** Her sayfadaki başlatıcının açtığı yan panel (tembel parça): sayfadaki asistanla aynı kanca ve sohbet. */
export default function AsistanPaneli() {
  const { pathname } = useLocation()
  const { props, hazir, ogretmen, sesOnay, instance } = useAsistanSohbeti('panel', sayfaAdi(pathname))
  // Küçültülmüş panel "Asistana sor" ile yeniden açılır (B78).
  useEffect(() => {
    const ac = () => { void instance.current?.changeView('mainWindow' as never) }
    window.addEventListener(ASISTANA_SOR, ac)
    return () => window.removeEventListener(ASISTANA_SOR, ac)
  }, [instance])
  const [tam, setTam] = useState(false)
  const kok = useRef<HTMLDivElement>(null)
  useEffect(() => (kok.current ? kaydirmaOdaginiYonet(kok.current) : undefined), [])
  useEffect(() => (kok.current ? carbonErisilebilirlikOnarimi(kok.current) : undefined), [])
  // Tam ekran: Carbon'un yüzen paneli pencereyi kaplar (float yerleşiminin kendi özellikleri). Yüzen pencerenin
  // genişliği messages-max-width ile de sınırlı (672 px); Carbon'da ikisi tek değişken, mesajlar da genişler.
  const boyut = tam ? { width: '100vw', height: '100dvh', 'max-width': '100vw', 'max-height': '100dvh',
    'min-height': '100dvh', 'messages-max-width': '100vw', 'bottom-position': '0px', 'right-position': '0px' }
    : { 'messages-max-width': MESAJ_GENISLIGI }
  const aile = ogretmen.secili?.renk_ailesi ?? null
  const gecmis = useGecmisGenisligi()
  return <div ref={kok} className={['asistan-paneli', tam && 'asistan-paneli--tam', aile && subjectClass(null, aile)].filter(Boolean).join(' ')}
    data-ogretmen={ogretmen.id} style={{ ...ogretmenDegiskenleri(aile), '--cds-aichat-history-width': gecmis } as CSSProperties}>
    {!hazir && <p className="app-shell-loading__text" role="status">Asistan yükleniyor…</p>}
    {hazir && <ChatContainer {...props} openChatByDefault
      layout={{ ...props.layout, customProperties: boyut }}
      header={{ ...props.header, actions: [...(props.header?.actions ?? []), { text: tam ? 'Küçült' : 'Tam ekran',
        icon: tam ? Minimize : Maximize, fixed: true, onClick: () => setTam(t => !t) }] }} />}
    {/* Sayfadaki gibi: öğrenciye aile notu, mikrofon onayı, ses hatası. */}
    <SesOnayi onay={sesOnay} />
    <SilmeOnayi />
  </div>
}
