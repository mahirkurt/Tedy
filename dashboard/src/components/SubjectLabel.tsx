import type { ReactNode } from 'react'
import type { SubjectFamily } from '../theme/subjects'
import { subjectClass } from '../utils/subject'

/**
 * A course name with its subject mark (Tedy ders renk sistemi).
 *
 * The mark is a small swatch in the subject family's accent — the same colour a
 * module uses for its rings and rules — and the name stays neutral text, so the
 * colour is never the only carrier of the subject (İ8).
 *
 * `children` replaces the printed name when the row already says more than the
 * course — an exam's title, "Matematik — Test 2" — while the mark still
 * resolves from the course.
 */
export default function SubjectLabel({ course, family, className, children }: {
  course: string | null | undefined
  family?: SubjectFamily | null
  className?: string
  children?: ReactNode
}) {
  return (
    <span className={['ted-subject-label', subjectClass(course, family), className].filter(Boolean).join(' ')}>
      <span className="ted-subject-label__mark" aria-hidden="true" />
      <span className="ted-subject-label__name">{children ?? course}</span>
    </span>
  )
}
