import { subjectFamily, type SubjectFamily } from '../theme/subjects'

/**
 * Class names that scope the subject roles (--ted-subject-*) from
 * theme/_subjects.scss onto an element. `family` lets a caller pass the
 * backend's `courseFamily` through instead of resolving the name again.
 */
export function subjectClass(course: string | null | undefined, family?: SubjectFamily | null): string {
  return `ted-subject ted-subject--${family ?? subjectFamily(course)}`
}
