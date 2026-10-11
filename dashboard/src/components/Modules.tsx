import {
  Button, ContainedList, ContainedListItem, InlineNotification, SkeletonText, Tag,
} from '@carbon/react'
import { useDar } from '../asistan/useDar'
import { Education } from '@carbon/icons-react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { apiHataCumlesi } from '../utils/apiHatasi'
import { useFocusMode } from '../contexts/focusMode'
import type { MufredatAgacYaniti } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import ModuleViewer from './ModuleViewer'
import MufredatAgaci from './MufredatAgaci'
import SubjectLabel from './SubjectLabel'
import './patterns/patterns.scss'
import './Modules.scss'

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const VERSION = /^v([1-9][0-9]{0,3})$/
const TASLAK = /^[0-9a-f]{16}$/

/** Internal mode codes never reach the reader (design constitution D4). */
const MODE_LABEL: Record<string, string> = {
  MODULE: 'Modül', QUIZ: 'Yarışma', FLASHCARDS: 'Kartlar', GAME: 'Oyun', EXPLAINER: 'Anlatım',
  ASSESSMENT: 'Değerlendirme', SERIES: 'Seri', CURRICULUM: 'Müfredat', EXAM: 'Sınav sorusu',
}

export default function Modules() {
  const { data, loading, iskelet, error, hataTuru } = useApi<MufredatAgacYaniti>(
    '/api/modules/agac', { hazir: [], dersler: [], kapsam: {}, hata: null })
  const hata = apiHataCumlesi(hataTuru ?? 'sunucu', 'Modüller')
  const navigate = useNavigate()
  const dar = useDar()
  const { focusMode } = useFocusMode()
  const hazir = Array.isArray(data.hazir) ? data.hazir : []
  const dersler = Array.isArray(data.dersler) ? data.dersler : []
  return (
    <div className="dashboard-card modules">
      <h2 className="dashboard-card__title"><Education size={20} />Modüller</h2>
      {/* S36/B48: eşik geçmeden iskelet çizilmez — bir kare yanıp sönen iskelet gürültüdür. */}
      {iskelet && <div aria-busy="true"><SkeletonText paragraph lineCount={3} /></div>}
      {!loading && error && (
        // B43 (D3, D4): the raw fetch error ("HTTP 500", "Non-JSON response") never reaches the reader.
        <InlineNotification kind="error" role="alert" lowContrast hideCloseButton statusIconDescription="Hata"
          title={hata.baslik} subtitle={hata.ayrinti} />
      )}
      {!loading && !error && (
        <>
          {hazir.length === 0
            ? <EmptyLine label="Hazır olanlar">Henüz yayınlanmış modül yok.</EmptyLine>
            : (
              <ContainedList className="module-hazir" kind="on-page" size="lg" label="Hazır olanlar">
                {hazir.map(m => (
                  <ContainedListItem key={`${m.slug}-${m.version}`}>
                    {/* B58: modül açmak gezinmedir — bağlantı olur, geçmiş ve yeni sekme çalışır. */}
                    <span className="module-hazir__metin">
                      <a className="module-hazir__bag" href={`/moduller/${m.slug}/v${m.version}`}
                        onClick={(e: React.MouseEvent) => {
                          e.preventDefault(); navigate(`/moduller/${m.slug}/v${m.version}`)
                        }}>
                        <SubjectLabel course={m.subject}>
                          <span className="module-hazir__ad">{m.title ?? m.slug}</span>
                        </SubjectLabel>
                      </a>
                      {/* İ8: ders rengi onun TEK taşıyıcısı olamaz — adı da yazılır. */}
                      <span className="module-hazir__ust-veri">
                        {[m.subject, m.gradeLevel].filter(Boolean).join(' · ')}
                      </span>
                    </span>
                    {m.mode && MODE_LABEL[m.mode] && (
                      <Tag type="cool-gray" size={dar ? 'md' : 'sm'}>{MODE_LABEL[m.mode]}</Tag>
                    )}
                  </ContainedListItem>
                ))}
              </ContainedList>
            )}
          {/* Odak kipinde ağaç çizilmez: yalnız yapılabilen iş kalır (İ1). */}
          {!focusMode && (data.hata === 'harita_okunamadi'
            ? <EmptyLine label="Tüm müfredat">Müfredat haritası şu an okunamıyor.</EmptyLine>
            : dersler.length > 0 && <MufredatAgaci dersler={dersler} />)}
        </>
      )}
    </div>
  )
}

export function ModuleViewerRoute() {
  const { slug = '', version = '' } = useParams<{ slug: string; version: string }>()
  const navigate = useNavigate()
  const match = VERSION.exec(version)
  if (!SLUG.test(slug) || !match) {
    return <div className="dashboard-card modules"><EmptyLine>Bu modül bağlantısı geçersiz.</EmptyLine></div>
  }
  const n = Number(match[1])
  return (
    <div className="module-page">
      <Button className="module-page__back" kind="ghost" size="md" href="/moduller"
        onClick={(e: React.MouseEvent) => { e.preventDefault(); navigate('/moduller') }}>Modüllere dön</Button>
      <ModuleViewer ticketPath={`/api/modules/${slug}/v${n}/ticket`} aciklamaPath={`/api/modules/${slug}/v${n}/aciklama`}
        title="Öğrenme modülü" progress={{ slug, version: n }} />
    </div>
  )
}

export function DraftViewerRoute() {
  const { taslakId = '' } = useParams<{ taslakId: string }>()
  if (!TASLAK.test(taslakId)) {
    return <div className="dashboard-card modules"><EmptyLine>Bu taslak bağlantısı geçersiz.</EmptyLine></div>
  }
  return (
    <div className="module-page">
      {/* B45 (§4.4): a sentence is not a Tag. */}
      <InlineNotification className="module-page__back module-page__taslak" kind="info" lowContrast hideCloseButton
        statusIconDescription="Bilgi" title="Taslak önizleme" subtitle="İlerleme kaydedilmez." />
      <ModuleViewer ticketPath={`/api/modules/taslak/${taslakId}/ticket`}
        aciklamaPath={`/api/modules/taslak/${taslakId}/aciklama`} title="Taslak modül önizlemesi" />
    </div>
  )
}
