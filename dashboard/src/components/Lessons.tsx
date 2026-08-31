import WeeklySchedule from './WeeklySchedule'
import CourseContent from './CourseContent'

/**
 * Dersler — the timetable and what is in those lessons, on one page.
 *
 * They were two surfaces because they arrive from two endpoints, which is our
 * problem rather than Işık's: "when is the lesson" and "what is in it" are the
 * same question asked twice, and answering them in two places means going to
 * the same course name twice (§1, §4.3).
 */
export default function Lessons() {
  return (
    <>
      <WeeklySchedule />
      <CourseContent />
    </>
  )
}
