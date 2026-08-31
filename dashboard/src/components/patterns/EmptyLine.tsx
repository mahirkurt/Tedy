import './patterns.scss'

export interface EmptyLineProps {
  /** What is not here. */
  children: React.ReactNode
  /**
   * Which section is empty. Needed when the empty line is the whole surface:
   * Dersler showed two bare sentences side by side and nothing said which
   * was the timetable and which was the lesson content.
   */
  label?: string
}

/**
 * The one shape an empty state takes.
 *
 * Nothing being there is not news, and it should not be announced with an icon
 * and a panel: on Bugün that treatment took roughly 200px directly under the
 * one thing the page exists to name, and competed with it (§2.3).
 */
export function EmptyLine({ children, label }: EmptyLineProps) {
  return (
    <p className="tedy-empty">
      {label && <span className="tedy-empty__label">{label}</span>}
      {children}
    </p>
  )
}
