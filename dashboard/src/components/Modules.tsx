import { Button, InlineNotification, SkeletonText, Tag } from '@carbon/react'
import { useDar } from '../asistan/useDar'
import { Education } from '@carbon/icons-react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { ModuleCard } from '../types'
import { EmptyLine } from './patterns/EmptyLine'
import ModuleViewer from './ModuleViewer'
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
  const { data, loading, error } = useApi<{ moduller: ModuleCard[] }>('/api/modules', { moduller: [] })
  const navigate = useNavigate()
  const dar = useDar()
  const modules = Array.isArray(data.moduller) ? data.moduller : []
  return (
    <div className="dashboard-card modules">
      <h2 className="dashboard-card__title"><Education size={20} />Modüller</h2>
      {loading && <SkeletonText paragraph lineCount={3} />}
      {!loading && error && (
        // B43 (D3, D4): the raw fetch error ("HTTP 500", "Non-JSON response") never reaches the reader.
        <InlineNotification kind="error" role="alert" lowContrast hideCloseButton statusIconDescription="Hata"
          title="Modüller yüklenemedi." subtitle="Sayfayı birkaç dakika sonra yeniden aç." />
      )}
      {!loading && !error && modules.length === 0 && (
        <EmptyLine label="Modüller">Henüz yayınlanmış modül yok.</EmptyLine>
      )}
      {modules.length > 0 && (
        <ul className="module-list">
          {modules.map(m => (
            <li key={m.slug} className="module-card">
              <div className="module-card__text">
                <span className="module-card__title">{m.title ?? m.slug}</span>
                <span className="module-card__meta">{[m.subject, m.gradeLevel].filter(Boolean).join(' · ')}</span>
              </div>
              {m.mode && MODE_LABEL[m.mode] && <Tag type="cool-gray" size="sm">{MODE_LABEL[m.mode]}</Tag>}
              {/* B17 (S12): the row action is tertiary — the page has no primary. B58: opening a module is
                  navigation, so it is a link (history, new tab); its name carries the module (B41). */}
              <Button kind="tertiary" size={dar ? 'lg' : 'md'} href={`/moduller/${m.slug}/v${m.version}`}
                aria-label={`Aç: ${m.title ?? m.slug}`}
                onClick={(e: React.MouseEvent) => { e.preventDefault(); navigate(`/moduller/${m.slug}/v${m.version}`) }}>
                Aç
              </Button>
            </li>
          ))}
        </ul>
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
      <ModuleViewer ticketPath={`/api/modules/${slug}/v${n}/ticket`} title="Öğrenme modülü" progress={{ slug, version: n }} />
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
      <ModuleViewer ticketPath={`/api/modules/taslak/${taslakId}/ticket`} title="Taslak modül önizlemesi" />
    </div>
  )
}
