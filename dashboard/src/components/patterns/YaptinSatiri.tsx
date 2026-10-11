import { useEffect, useRef } from 'react'
import { Button, InlineLoading } from '@carbon/react'
import { Checkmark } from '@carbon/icons-react'
import './patterns.scss'

export type GeriAlDurumu = 'bos' | 'aliniyor' | 'hata'

/**
 * The quiet line after "Yaptım": what was recorded, and "Geri al" on the same
 * line (talimatname S40, B63; İ5). "Yaptım" is low impact and easy to undo, so
 * it is done without a confirmation and taken back here — Carbon's low-impact
 * pattern (common actions, "Low-impact deletion"). A ghost button, because the
 * line is a footnote to the card, never a second primary action (İ1).
 *
 * No timer takes "Geri al" away: a control that vanishes after ten seconds is
 * a race the reader can lose (WCAG 2.2.1), and losing it is exactly the slip
 * the button is for. It stays until the page moves on.
 *
 * Shared by Bugün and İşler so both say it with the same words (İ9).
 */
export function YaptinSatiri({
  ad, durum, onGeriAl, size = 'lg', className = '',
}: {
  ad: string
  durum: GeriAlDurumu
  onGeriAl: () => void
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  // B40 (D2): after "Yaptım" the row it was pressed on moves or goes; focus lands here — on what was recorded —
  // instead of falling to the page, and the next Tab reaches "Geri al".
  const metinRef = useRef<HTMLParagraphElement>(null)
  useEffect(() => { metinRef.current?.focus() }, [ad])
  return (
    <div className={['yaptin-satiri', className].filter(Boolean).join(' ')}>
      <p className="yaptin-satiri__metin" role="status" tabIndex={-1} ref={metinRef}>
        <Checkmark size={16} />
        <span>Yaptın: {ad}</span>
      </p>
      {durum === 'aliniyor' ? (
        <InlineLoading className="yaptin-satiri__yukleniyor" description="Geri alınıyor…"
          iconDescription="Geri alınıyor" status="active" />
      ) : (
        <Button kind="ghost" size={size} className="yaptin-satiri__geri-al" onClick={onGeriAl}>
          Geri al
        </Button>
      )}
      {durum === 'hata' && (
        <p className="yaptin-satiri__hata" role="alert">
          Geri alınamadı. Bağlantını kontrol edip yeniden dene.
        </p>
      )}
    </div>
  )
}
