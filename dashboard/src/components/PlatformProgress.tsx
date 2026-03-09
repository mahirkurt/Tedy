import { ProgressBar, Tag } from '@carbon/react'
import { ChartBar } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'

export default function PlatformProgress() {
  const { data: ec } = useApi<{ total_videos?: number; completed_videos?: number }>(
    '/api/progress/ec', {}
  )
  const { data: a3k } = useApi<{
    teacher_assigned_count?: number; teacher_assigned_completed?: number
    dashboard_stats?: { completed?: number; target?: number; firstTryScore?: number }
  }>('/api/progress/a3k', {})
  const { data: sebit } = useApi<{ total_homework?: number; completed_count?: number }>(
    '/api/sebit', {}
  )

  const platforms = [
    { name: 'EnglishCentral', done: ec.completed_videos || 0, total: ec.total_videos || 0 },
    { name: 'Achieve3000', done: a3k.teacher_assigned_completed || 0, total: a3k.teacher_assigned_count || 0 },
    { name: 'SEBIT', done: sebit.completed_count || 0, total: sebit.total_homework || 0 }
  ]

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <ChartBar size={20} />
        Platform İlerleme
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {platforms.map(p => {
          const pct = p.total > 0 ? Math.round((p.done / p.total) * 100) : 0
          return (
            <div key={p.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 500, fontSize: '0.8125rem' }}>{p.name}</span>
                <Tag type={pct === 100 ? 'green' : pct > 50 ? 'blue' : 'warm-gray'} size="sm">
                  {p.done}/{p.total}
                </Tag>
              </div>
              <ProgressBar label={p.name} value={pct} status={pct === 100 ? 'finished' : 'active'} size="small" hideLabel />
            </div>
          )
        })}
      </div>
      {a3k.dashboard_stats?.firstTryScore && (
        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#525252' }}>
          A3K Ilk Deneme Skoru: <strong>{a3k.dashboard_stats.firstTryScore}</strong>
        </div>
      )}
    </div>
  )
}
