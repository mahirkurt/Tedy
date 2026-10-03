import { Button } from '@carbon/react'

export default function NetlestirmeSecenekleri({ secenekler, etkin, onSec, onBaska }: {
  secenekler: string[]
  etkin: boolean
  onSec: (secenek: string) => void
  onBaska: () => void
}) {
  return <div className="ac-netlestirme" role="group" aria-label="Seçenekler">
    {secenekler.map(secenek => <Button key={secenek} kind="tertiary" size="sm"
      disabled={!etkin} onClick={() => onSec(secenek)}>{secenek}</Button>)}
    <Button kind="ghost" size="sm" disabled={!etkin} onClick={onBaska}>Başka bir şey yaz…</Button>
  </div>
}
