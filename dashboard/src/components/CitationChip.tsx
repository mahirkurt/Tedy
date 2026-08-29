import { useState } from 'react'
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
}

// `citation.kind` is a closed union at compile time but an unchecked string
// off the wire at runtime — a backend value outside the four known kinds
// must not turn into the literal word "undefined" leaking into the
// accessible name or the popover body.
const UNKNOWN_KIND_LABEL = 'Kaynak'

export default function CitationChip({ citation, onActivate }: Props) {
  const [open, setOpen] = useState(false)
  const kindLabel = KIND_LABEL[citation.kind] ?? UNKNOWN_KIND_LABEL

  return (
    <Popover open={open} align="bottom" autoAlign caret dropShadow={false}>
      <button
        type="button"
        className="ac-cite"
        aria-label={`${kindLabel}: ${citation.label}`}
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
        <p className="ac-cite__snippet">{citation.snippet}</p>
      </PopoverContent>
    </Popover>
  )
}
