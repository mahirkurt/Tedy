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

export default function CitationChip({ citation, onActivate }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <Popover open={open} align="bottom" autoAlign caret dropShadow={false}>
      <button
        type="button"
        className="ac-cite"
        aria-label={`${KIND_LABEL[citation.kind]}: ${citation.label}`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => onActivate(citation.id)}
      >
        {citation.id.replace('S', '')}
      </button>
      <PopoverContent className="ac-cite__pop">
        <span className="ac-cite__kind">{KIND_LABEL[citation.kind]}</span>
        <strong className="ac-cite__label">{citation.label}</strong>
        <p className="ac-cite__snippet">{citation.snippet}</p>
      </PopoverContent>
    </Popover>
  )
}
