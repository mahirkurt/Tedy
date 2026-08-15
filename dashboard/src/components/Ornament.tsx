/**
 * Printer's fleuron, drawn rather than typed.
 *
 * The obvious choice — a ❦ character — falls through to the colour emoji font
 * on most systems and lands as an orange blob. An inline SVG inherits
 * `currentColor`, scales cleanly, and looks the same everywhere.
 */
export default function Ornament({ variant = 'full' }: { variant?: 'full' | 'mark' }) {
  if (variant === 'mark') {
    return (
      <svg className="ornament ornament--mark" viewBox="0 0 12 12" aria-hidden focusable="false">
        <path d="M6 0.5 L7.7 6 L6 11.5 L4.3 6 Z" fill="currentColor" />
      </svg>
    )
  }

  return (
    <svg className="ornament" viewBox="0 0 72 12" aria-hidden focusable="false">
      <path d="M0 6h23M49 6h23" stroke="currentColor" strokeWidth="1" />
      <path d="M36 1 L39.4 6 L36 11 L32.6 6 Z" fill="currentColor" />
      <circle cx="27" cy="6" r="1.2" fill="currentColor" />
      <circle cx="45" cy="6" r="1.2" fill="currentColor" />
    </svg>
  )
}
