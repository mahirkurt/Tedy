import { useEffect, useRef, useState } from 'react'
import { Button, IconButton } from '@carbon/react'
import { Attachment, Camera } from '@carbon/icons-react'

/** One picker for chat attachments and homework documents, including phone capture. */
export default function YuklemeAlani({ onDosyalar, disabled = false, belge = false }: {
  onDosyalar: (files: File[]) => void
  disabled?: boolean
  belge?: boolean
}) {
  const dosya = useRef<HTMLInputElement>(null)
  const kamera = useRef<HTMLInputElement>(null)
  const [dokunmatik, setDokunmatik] = useState(() => window.matchMedia('(pointer: coarse)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(pointer: coarse)')
    const degistir = () => setDokunmatik(mq.matches)
    mq.addEventListener('change', degistir)
    return () => mq.removeEventListener('change', degistir)
  }, [])
  return <>
    <input ref={dosya} className="cds--visually-hidden ac__dosya-girdi" type="file" multiple={!belge}
      accept={belge ? '.pdf,.docx,.txt,.md' : 'image/*,.pdf,.docx,.txt,.md'}
      aria-hidden tabIndex={-1} disabled={disabled}
      onChange={e => { onDosyalar([...e.target.files || []]); e.target.value = '' }} />
    {belge
      ? <Button kind="secondary" size="sm" disabled={disabled} onClick={() => dosya.current?.click()}>
        {disabled ? 'Ekleniyor…' : 'Belge ekle'}</Button>
      : <IconButton kind="ghost" size="lg" label="Dosya ekle" disabled={disabled}
        onClick={() => dosya.current?.click()}><Attachment /></IconButton>}
    {!belge && dokunmatik && <>
      <input ref={kamera} className="cds--visually-hidden ac__dosya-girdi ac__dosya-girdi--kamera" type="file"
        accept="image/*" capture="environment" aria-hidden tabIndex={-1} disabled={disabled}
        onChange={e => { onDosyalar([...e.target.files || []]); e.target.value = '' }} />
      <IconButton kind="ghost" size="lg" label="Fotoğraf çek" disabled={disabled}
        onClick={() => kamera.current?.click()}><Camera /></IconButton>
    </>}
  </>
}
