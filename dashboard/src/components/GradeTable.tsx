import { useApi } from '../hooks/useApi'
import { Certificate } from '@carbon/icons-react'
import type { GradeItem } from '../types'
import { gradeColor } from '../utils/formatters'
import type { CSSProperties } from 'react'

const COLS = ['1. Sınav', '2. Sınav', '3. Sınav', 'DİKP/Performans-1', 'DİKP/Performans-2', 'DİKP/Performans-3'] as const
const COL_SHORT = ['S1', 'S2', 'S3', 'P1', 'P2', 'P3']

const thStyle: CSSProperties = {
  padding: '0.5rem 0.75rem', textAlign: 'center',
  borderBottom: '2px solid #E0E0E0', backgroundColor: '#F4F4F4', fontSize: '0.75rem'
}
const tdStyle: CSSProperties = {
  padding: '0.5rem 0.75rem', borderBottom: '1px solid #E0E0E0'
}

export default function GradeTable() {
  const { data } = useApi<{ semester?: string; grades?: GradeItem[] }>(
    '/api/grades', {}
  )

  const grades = data.grades || []

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Certificate size={20} />
        Notlar &mdash; {data.semester || ''}
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
          <thead>
            <tr>
              <th style={{ ...thStyle, textAlign: 'left' }}>Ders</th>
              {COL_SHORT.map(c => <th key={c} style={thStyle}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {grades.map((g, i) => (
              <tr key={i}>
                <td style={{ ...tdStyle, fontWeight: 500 }}>{g.Ders}</td>
                {COLS.map((col, ci) => {
                  const val = g[col]
                  const color = gradeColor(val)
                  return (
                    <td key={ci} style={{
                      ...tdStyle,
                      textAlign: 'center',
                      fontWeight: 600,
                      color: color || '#161616',
                      backgroundColor: val !== '-' && color ? `${color}11` : 'transparent'
                    }}>
                      {val}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
