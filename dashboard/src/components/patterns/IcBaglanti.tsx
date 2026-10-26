import type { ReactNode } from 'react'
import { Link as CarbonLink } from '@carbon/react'
import { useIcGezinme } from '../../hooks/useIcGezinme'

/** A Carbon link that stays in the app on a plain click and leaves every other click — a new tab,
 *  a new window, an outside address — to the browser (C13). Shared by the exam card and the module page. */
export default function IcBaglanti({ href, children, size, inline }: {
  href: string
  children: ReactNode
  size?: 'sm'
  /** Carbon's inline link, for a link inside a sentence. */
  inline?: boolean
}) {
  return <CarbonLink href={href} size={size} inline={inline} onClick={useIcGezinme(href)}>{children}</CarbonLink>
}
