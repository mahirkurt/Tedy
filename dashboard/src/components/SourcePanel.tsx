import { useEffect, useRef } from 'react'
import { Tile } from '@carbon/react'
import { DocumentView } from '@carbon/icons-react'
import type { AssistantCitation, CitationKind } from '../types'

const GROUP_ORDER: CitationKind[] = ['ogrenci', 'mufredat', 'kitap', 'oer']

const GROUP_TITLE: Record<CitationKind, string> = {
  ogrenci: 'Işık’ın okul verisi',
  mufredat: 'MEB müfredatı',
  kitap: 'Ders kitabı',
  oer: 'Açık eğitsel kaynak',
}

interface Props {
  citations: AssistantCitation[]
  activeId: string | null
}

export default function SourcePanel({ citations, activeId }: Props) {
  const activeRef = useRef<HTMLLIElement>(null)

  useEffect(() => {
    if (activeId) activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [activeId])

  if (citations.length === 0) {
    return (
      <Tile className="ac__panel">
        <h4 className="ac__panel-title"><DocumentView size={16} /> Kaynaklar</h4>
        <p className="ac__muted">Soru sorduğunda kaynaklar burada görünecek.</p>
      </Tile>
    )
  }

  return (
    <Tile className="ac__panel">
      <h4 className="ac__panel-title"><DocumentView size={16} /> Kaynaklar</h4>
      {GROUP_ORDER.map(kind => {
        const group = citations.filter(c => c.kind === kind)
        if (group.length === 0) return null
        return (
          <section key={kind} className="ac__ref-group">
            <h5 className="ac__ref-group-title">{GROUP_TITLE[kind]}</h5>
            <ul className="ac__ref-list">
              {group.map(c => (
                <li
                  key={c.id}
                  ref={c.id === activeId ? activeRef : undefined}
                  className={`ac__ref-item${c.id === activeId ? ' ac__ref-item--active' : ''}`}
                >
                  <span className="ac__ref-index">{c.id.replace('S', '')}</span>
                  <div>
                    <span className="ac__ref-path">{c.label}</span>
                    <p className="ac__ref-snippet">{c.snippet}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </Tile>
  )
}
