import SourcePanel from '../components/SourcePanel'
import { useAsistanDurumu } from './asistanDeposu.ts'

/** Workspace panelinin içeriği: bugünkü kaynak paneli, son açılan cevabın atıflarıyla. */
export default function KaynakPaneli() {
  const acik = useAsistanDurumu(d => d.acikAtif)
  if (!acik) return null
  return <div className="asistan__kaynaklar"><SourcePanel citations={acik.atiflar} activeId={acik.etkin} /></div>
}
