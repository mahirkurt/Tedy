import { Tabs, TabList, Tab, TabPanels, TabPanel, Tile } from '@carbon/react'
import { Education } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'

interface CourseData {
  [course: string]: {
    tab_id?: string
    text?: string
    cards?: string[]
    items?: unknown[]
  }
}

export default function CourseContent() {
  const { data } = useApi<CourseData>('/api/content', {})

  const courses = Object.entries(data).filter(([, v]) =>
    v && (v.text || (v.cards && v.cards.length > 0))
  )

  if (courses.length === 0) return null

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Education size={20} />
        Ders İçerikleri
      </h4>
      <Tabs>
        <TabList aria-label="Ders içerikleri" contained>
          {courses.map(([name]) => (
            <Tab key={name}>{name}</Tab>
          ))}
        </TabList>
        <TabPanels>
          {courses.map(([name, content]) => (
            <TabPanel key={name}>
              {content.text && (
                <div style={{
                  fontSize: '0.8125rem', lineHeight: '1.5',
                  whiteSpace: 'pre-wrap', padding: '0.5rem 0'
                }}>
                  {content.text.slice(0, 1000)}
                </div>
              )}
              {content.cards && content.cards.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', marginTop: '0.5rem' }}>
                  {content.cards.slice(0, 5).map((card, i) => (
                    <Tile key={i} style={{ padding: '0.5rem 1rem', fontSize: '0.8125rem' }}>
                      {card.slice(0, 300)}
                    </Tile>
                  ))}
                </div>
              )}
            </TabPanel>
          ))}
        </TabPanels>
      </Tabs>
    </div>
  )
}
