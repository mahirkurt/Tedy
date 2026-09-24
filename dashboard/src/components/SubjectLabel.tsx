import type { SubjectFamily } from '../theme/subjects'
import { subjectClass } from '../utils/subject'

/**
 * A course name with its subject mark (Tedy ders renk sistemi).
 *
 * The mark is a small swatch in the subject family's accent — the same colour a
 * module uses for its rings and rules — and the name stays neutral text, so the
 * colour is never the only carrier of the subject (İ8).
 */
export default function SubjectLabel({ course, family, className }: {
  course: string
  family?: SubjectFamily | null
  className?: string
}) {
  return (
    <span className={['ted-subject-label', subjectClass(course, family), className].filter(Boolean).join(' ')}>
      <span className="ted-subject-label__mark" aria-hidden="true" />
      <span className="ted-subject-label__name">{course}</span>
    </span>
  )
}
