import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import { Tile } from '@carbon/react'
import { DocumentView } from '@carbon/icons-react'
import type { AssistantCitation, CitationKind } from '../types'

const GROUP_ORDER: CitationKind[] = ['ogrenci', 'mufredat', 'kitap', 'oer']
const KNOWN_KINDS = new Set<string>(GROUP_ORDER)

const GROUP_TITLE: Record<CitationKind, string> = {
  ogrenci: 'Işık’ın okul verisi',
  mufredat: 'MEB müfredatı',
  kitap: 'Ders kitabı',
  oer: 'Açık eğitsel kaynak',
}

// A citation whose `kind` is not one of the four known authorities. This is
// a runtime possibility even though `CitationKind` is a closed union at
// compile time — the value comes from the backend over JSON, unchecked.
// Silently dropping it (the old `GROUP_ORDER.map` + `filter` pattern) made
// the citation vanish from the panel entirely while its inline chip kept
// rendering, so it read as a dead click. It gets its own clearly-labelled
// group instead — never folded into `ogrenci` or `mufredat`, since the
// authority split is the thing readers rely on to tell "Işık's own data"
// apart from "MEB says so".
const UNCLASSIFIED_TITLE = 'Sınıflandırılmamış kaynak'

interface Props {
  citations: AssistantCitation[]
  activeId: string | null
}

function RefGroup({
  title,
  items,
  activeId,
  activeRef,
}: {
  title: string
  items: AssistantCitation[]
  activeId: string | null
  activeRef: RefObject<HTMLLIElement | null>
}) {
  return (
    <section className="ac__ref-group">
      <h5 className="ac__ref-group-title">{title}</h5>
      <ul className="ac__ref-list">
        {items.map(c => (
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
}

export default function SourcePanel({ citations, activeId }: Props) {
  const activeRef = useRef<HTMLLIElement>(null)

  useEffect(() => {
    if (activeId) activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [activeId])

  const unclassified = citations.filter(c => !KNOWN_KINDS.has(c.kind))

  if (unclassified.length > 0) {
    // A backend-sent `kind` outside the known union should not fail
    // quietly — it still renders (see the unclassified group below), but
    // this is worth a developer-visible signal, since it usually means a
    // new citation kind was added server-side without a matching group
    // here.
    console.warn(
      `SourcePanel: ${unclassified.length} citation(s) with an unrecognised kind`,
      unclassified.map(c => ({ id: c.id, kind: c.kind })),
    )
  }

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
          <RefGroup
            key={kind}
            title={GROUP_TITLE[kind]}
            items={group}
            activeId={activeId}
            activeRef={activeRef}
          />
        )
      })}
      {unclassified.length > 0 && (
        <RefGroup
          key="unclassified"
          title={UNCLASSIFIED_TITLE}
          items={unclassified}
          activeId={activeId}
          activeRef={activeRef}
        />
      )}
    </Tile>
  )
}
