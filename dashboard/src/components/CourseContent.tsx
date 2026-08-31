import { Tabs, TabList, Tab, TabPanels, TabPanel, Accordion, AccordionItem, Tag } from '@carbon/react'
import { Education } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import { COURSE_CONTENT_ORDER, normalizeCourseDisplayName } from '../utils/formatters'
import { EmptyLine } from './patterns/EmptyLine'

interface CourseData {
  [course: string]: {
    tab_id?: string
    text?: string
    cards?: string[]
    items?: unknown[]
  }
}

interface ParsedCard {
  raw: string
  weekNum: number | null
  teacher: string | null
  date: string | null
  body: string
}

function parseCard(card: string): ParsedCard {
  const lines = card.split('\n').map(l => l.trim()).filter(Boolean)

  // Extract week number
  const weekMatch = card.match(/(\d+)\.\s*HAFTA/i)
  const weekNum = weekMatch ? parseInt(weekMatch[1], 10) : null

  // Extract teacher + date: pattern "Teacher Name | DD.MM.YYYY"
  let teacher: string | null = null
  let date: string | null = null
  for (const line of lines) {
    const pipeMatch = line.match(/^(.+?)\s*\|\s*(\d{2}\.\d{2}\.\d{4})/)
    if (pipeMatch) {
      teacher = pipeMatch[1].trim()
      date = pipeMatch[2].trim()
      break
    }
  }

  // Build clean body: remove week header line, teacher|date line
  const bodyLines = lines.filter(line => {
    if (line.match(/^\d+\.\s*HAFTA/i)) return false
    if (line.match(/^.+?\s*\|\s*\d{2}\.\d{2}\.\d{4}/)) return false
    return true
  })

  return { raw: card, weekNum, teacher, date, body: bodyLines.join('\n') }
}

interface WeekGroup {
  weekNum: number
  cards: ParsedCard[]
  latestDate: string | null
}

function groupByWeek(cards: ParsedCard[]): WeekGroup[] {
  const map = new Map<number, ParsedCard[]>()
  const noWeek: ParsedCard[] = []

  for (const card of cards) {
    if (card.weekNum === null) {
      noWeek.push(card)
    } else {
      const existing = map.get(card.weekNum) || []
      existing.push(card)
      map.set(card.weekNum, existing)
    }
  }

  const groups: WeekGroup[] = []
  map.forEach((groupCards, weekNum) => {
    // Pick the latest date among cards in this week
    const dates = groupCards.map(c => c.date).filter(Boolean) as string[]
    const latestDate = dates.length > 0 ? dates[dates.length - 1] : null
    groups.push({ weekNum, cards: groupCards, latestDate })
  })

  // Sort descending by week number (most recent first)
  groups.sort((a, b) => b.weekNum - a.weekNum)

  // Add ungrouped cards as a synthetic group at the end
  if (noWeek.length > 0) {
    groups.push({ weekNum: -1, cards: noWeek, latestDate: null })
  }

  // Keep only the most recent 4 weeks
  return groups.slice(0, 4)
}

export default function CourseContent() {
  const { data } = useApi<CourseData>('/api/content', {})
  const { focusMode } = useFocusMode()

  const mergedCourses = new Map<string, CourseData[string]>()

  for (const [rawName, content] of Object.entries(data)) {
    if (!content) continue
    const normalized = normalizeCourseDisplayName(rawName)
    const existing = mergedCourses.get(normalized)
    if (!existing) {
      mergedCourses.set(normalized, {
        ...content,
        text: content.text || '',
        cards: [...(content.cards || [])],
        items: [...(content.items || [])],
      })
      continue
    }

    const mergedText = [existing.text, content.text].filter(Boolean).join('\n\n').trim()
    const mergedCards = [...(existing.cards || []), ...(content.cards || [])]
    const mergedItems = [...(existing.items || []), ...(content.items || [])]

    mergedCourses.set(normalized, {
      ...existing,
      text: mergedText,
      cards: Array.from(new Set(mergedCards)),
      items: Array.from(new Set(mergedItems)),
    })
  }

  const orderedNames = COURSE_CONTENT_ORDER.filter(name => mergedCourses.has(name))
  const courses = orderedNames.map(name => [name, mergedCourses.get(name)!] as const).filter(([, v]) =>
    v && (v.text || (v.cards && v.cards.length > 0))
  )

  if (courses.length === 0) {
    return <EmptyLine>Derslere ait içerik henüz yok.</EmptyLine>
  }

  return (
    <div className="dashboard-card">
      <h2 className="dashboard-card__title">
        <Education size={20} />
        Ders İçerikleri
      </h2>
      <Tabs>
        <TabList aria-label="Ders içerikleri" contained>
          {courses.map(([name]) => (
            <Tab key={name}>{name}</Tab>
          ))}
        </TabList>
        <TabPanels>
          {courses.map(([name, content]) => {
            const hasCards = content.cards && content.cards.length > 0

            // Deduplicate consecutive cards where one is a prefix/subset of the other
            const deduped = hasCards
              ? content.cards!.filter((card, i, arr) => {
                  if (i === arr.length - 1) return true
                  const next = arr[i + 1]
                  return !next.startsWith(card) && !card.startsWith(next)
                })
              : []

            const parsed = deduped.map(parseCard)
            const weekGroups = groupByWeek(parsed)
            const hasWeeks = weekGroups.some(g => g.weekNum !== -1)

            return (
              <TabPanel key={name}>
                {!hasCards && content.text && (
                  <Accordion>
                    <AccordionItem
                      title={content.text.slice(0, 80) + (content.text.length > 80 ? '…' : '')}
                      open={!focusMode}
                    >
                      <div className="course-content-text">
                        {content.text.slice(0, 1000)}
                      </div>
                    </AccordionItem>
                  </Accordion>
                )}
                {hasCards && hasWeeks && (
                  <Accordion className="course-content-accordion">
                    {weekGroups.map((group) => {
                      const weekLabel = group.weekNum === -1
                        ? 'Diğer'
                        : `${group.weekNum}. Hafta`
                      const dateLabel = group.latestDate ? ` — ${group.latestDate}` : ''
                      const title = (
                        <span className="course-content__week-header">
                          <span className="course-content__week-label">{weekLabel}</span>
                          {dateLabel && (
                            <span className="course-content__week-date">{dateLabel}</span>
                          )}
                          <Tag type="cool-gray" size="sm" className="course-content__week-count">
                            {group.cards.length} içerik
                          </Tag>
                        </span>
                      )
                      return (
                        <AccordionItem
                          key={group.weekNum}
                          title={title as unknown as string}
                          open={!focusMode && weekGroups.indexOf(group) === 0}
                        >
                          <div className="course-content__cards">
                            {group.cards.map((card, i) => (
                              <div key={i} className="course-content__card-item">
                                {(card.teacher || card.date) && (
                                  <div className="course-content__card-meta">
                                    {card.teacher && <span className="course-content__card-teacher">{card.teacher}</span>}
                                    {card.date && <span className="course-content__card-date">{card.date}</span>}
                                  </div>
                                )}
                                <div className="course-content-text">
                                  {card.body || card.raw.slice(0, 500)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </AccordionItem>
                      )
                    })}
                  </Accordion>
                )}
                {hasCards && !hasWeeks && (
                  <Accordion className="course-content-accordion">
                    {deduped.slice(0, 8).map((card, i) => (
                      <AccordionItem
                        key={i}
                        title={card.slice(0, 80) + (card.length > 80 ? '…' : '')}
                      >
                        <div className="course-content-text">
                          {card}
                        </div>
                      </AccordionItem>
                    ))}
                  </Accordion>
                )}
              </TabPanel>
            )
          })}
        </TabPanels>
      </Tabs>
    </div>
  )
}
