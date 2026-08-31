import './patterns.scss'

export interface EmptyLineProps {
  /** What is not here. */
  children: React.ReactNode
}

/**
 * The one shape an empty state takes.
 *
 * Nothing being there is not news, and it should not be announced with an icon
 * and a panel: on Bugün that treatment took roughly 200px directly under the
 * one thing the page exists to name, and competed with it (§2.3).
 */
export function EmptyLine({ children }: EmptyLineProps) {
  return <p className="tedy-empty">{children}</p>
}
