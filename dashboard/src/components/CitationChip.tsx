import { useId, useState } from 'react'
import { Popover, PopoverContent } from '@carbon/react'
import type { AssistantCitation } from '../types'

interface Props {
  citation: AssistantCitation
  onActivate: (id: string) => void
}

const KIND_LABEL: Record<AssistantCitation['kind'], string> = {
  ogrenci: 'Okul verisi',
  mufredat: 'MEB müfredatı',
  kitap: 'Ders kitabı',
  oer: 'Açık kaynak',
  modul: 'Yayınlanmış modül',
  'tedy-kitap': 'Tedy Books',
  'aile-kaynak': 'Aile kaynağı',
}

// `citation.kind` is a closed union at compile time but an unchecked string
// off the wire at runtime — a backend value outside the known kinds above
// must not turn into the literal word "undefined" leaking into the
// accessible name or the popover body.
const UNKNOWN_KIND_LABEL = 'Kaynak'

export default function CitationChip({ citation, onActivate }: Props) {
  const [open, setOpen] = useState(false)
  const kindLabel = KIND_LABEL[citation.kind] ?? UNKNOWN_KIND_LABEL

  // The same citation id appears in more than one answer in a session, so the
  // id has to be unique per rendered chip rather than derived from S1/S2.
  const snippetId = `${useId()}-snippet`
  // aria-label already carries the kind and the label; the description is what
  // the source SAYS. Without this the popover is visual-only and a screen
  // reader announces which book was cited but nothing it claimed (D2). Left
  // unset when there is no snippet, so the chip is never pointed at an
  // empty element.
  const describedBy = citation.snippet ? snippetId : undefined

  return (
    <Popover open={open} align="bottom" autoAlign caret dropShadow={false}>
      <button
        type="button"
        className="ac-cite"
        aria-label={`${kindLabel}: ${citation.label}`}
        aria-describedby={describedBy}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => onActivate(citation.id)}
      >
        {citation.id.replace('S', '')}
      </button>
      <PopoverContent className="ac-cite__pop">
        <span className="ac-cite__kind">{kindLabel}</span>
        <strong className="ac-cite__label">{citation.label}</strong>
        <p className="ac-cite__snippet" id={snippetId}>{citation.snippet}</p>
      </PopoverContent>
    </Popover>
  )
}
