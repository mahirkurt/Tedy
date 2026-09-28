import { Button } from '@carbon/react'
import { ArrowRight } from '@carbon/icons-react'
import type { ModOnerisi as Oneri } from '../types'
import { subjectClass } from '../utils/subject'

/**
 * The assistant's suggestion to move to a subject teacher (mod_oner, spec §1 "Otomatik
 * öneri"). A button, never a switch: the mode changes only when the reader presses it. The
 * left edge is the suggested subject's colour; the model's one-sentence reason sits above.
 */
export default function ModOnerisi({ oneri, onGec }: { oneri: Oneri; onGec: () => void }) {
  return (
    <div className={`ac-msg__oneri ${subjectClass(null, oneri.renk_ailesi)}`}>
      <p className="ac-msg__oneri-gerekce">{oneri.gerekce}</p>
      <Button kind="tertiary" size="sm" renderIcon={ArrowRight} onClick={onGec}>
        {oneri.soru}
      </Button>
    </div>
  )
}
