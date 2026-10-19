import { useEffect, useMemo, useState } from 'react'
import { Accordion, AccordionItem, Link } from '@carbon/react'
import { CircleFilled, Launch, Notification } from '@carbon/icons-react'
import { useSession } from '../contexts/session'
import { useApi } from '../hooks/useApi'
import { useFocusMode } from '../contexts/focusMode'
import type { Announcement } from '../types'
import { formatTurkishDate } from '../utils/formatters'
import { EmptyLine } from './patterns/EmptyLine'
import { EkBaglantisi } from './patterns/EkBaglantisi'
import { Rakamli } from './patterns/Rakamli'

const DETAIL_FIELDS = [
  'e-Posta İçerik',
  'Duyuru Detayı',
  'İçerik',
  'Açıklama',
  'Mesaj',
] as const

function getAnnouncementDetail(ann: Announcement): string {
  for (const field of DETAIL_FIELDS) {
    const value = ann[field]
    if (typeof value === 'string' && value.trim() && value.trim() !== '-') return value.trim()
  }
  return 'Detay bulunamadı.'
}

/** dd.mm.yyyy[ hh:mm] → epoch ms for ordering; an unreadable date sinks. */
function zamani(dateStr?: string | null): number {
  const m = (dateStr || '').match(/(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}))?/)
  if (!m) return 0
  return new Date(+m[3], +m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0)).getTime()
}

/** A stable key per announcement (title + publication time): what "read" is remembered by. */
function duyuruAnahtari(ann: Announcement): string {
  return `${ann["Yayın Tarihi"] || ''}|${ann["e-Posta Başlık"] || ''}`
}

// B67 (§4.8, İ5): unread is remembered per person on this device. localStorage can be missing or throw
// (private window, blocked storage); then nothing is remembered and every announcement reads as new.
const okunduAnahtari = (email?: string | null) => `tedy-duyurular-okundu::${email || 'anonim'}`

function okunanlariOku(email?: string | null): Set<string> {
  try {
    const ham = window.localStorage.getItem(okunduAnahtari(email))
    return new Set(ham ? (JSON.parse(ham) as string[]) : [])
  } catch {
    return new Set()
  }
}

function okunanlariYaz(email: string | null | undefined, anahtarlar: Set<string>) {
  try {
    // Only the last 200: the portal's list is far shorter, and the key must not grow for ever.
    window.localStorage.setItem(okunduAnahtari(email), JSON.stringify([...anahtarlar].slice(-200)))
  } catch { /* storage unavailable: nothing to remember */ }
}

export default function Announcements() {
  const { data } = useApi<{ announcements: Announcement[] }>(
    '/api/announcements', { announcements: [] }
  )
  const { focusMode } = useFocusMode()
  const user = useSession()
  // Read once when the page opens: what was unread now stays marked for this visit, then counts as seen.
  const [okunanlar] = useState(() => okunanlariOku(user?.email))

  const sirali = useMemo(
    () => [...data.announcements].sort((a, b) => zamani(b["Yayın Tarihi"]) - zamani(a["Yayın Tarihi"])),
    [data.announcements])

  useEffect(() => {
    if (sirali.length === 0) return
    const yeni = new Set(okunanlar)
    sirali.forEach(a => yeni.add(duyuruAnahtari(a)))
    okunanlariYaz(user?.email, yeni)
  }, [sirali, okunanlar, user?.email])

  if (data.announcements.length === 0) {
    return <EmptyLine label="Okul Duyuruları">Okuldan yeni bir duyuru yok.</EmptyLine>
  }

  const okunmamis = sirali.filter(a => !okunanlar.has(duyuruAnahtari(a)))
  // Focus mode: only what is new (or, when nothing is, the latest one).
  const gorunen = focusMode ? (okunmamis.length > 0 ? okunmamis : sirali.slice(0, 1)) : sirali

  return (
    <div className="dashboard-card">
      <h2 className="dashboard-card__title">
        <Notification size={20} />
        Okul Duyuruları
      </h2>
      {okunmamis.length > 0 && (
        <p className="announcements__ozet">{okunmamis.length} yeni duyuru</p>
      )}
      {/* Newest first, one list; an unread announcement opens by itself and says it is new (§2.5, §4.8). */}
      <Accordion className="announcements-list">
        {gorunen.map(ann => {
          const anahtar = duyuruAnahtari(ann)
          const yeni = !okunanlar.has(anahtar)
          return (
            <AccordionItem
              key={anahtar}
              open={yeni}
              className={yeni ? 'announcements-item announcements-item--yeni' : 'announcements-item'}
              title={
                <span className="announcements-item__baslik">
                  {yeni && <span className="announcements-item__yeni"><CircleFilled size={16} aria-hidden="true" />Yeni</span>}
                  <span className="announcements-item__ad">{ann["e-Posta Başlık"]}</span>
                  <span className="announcements-item__tarih"><Rakamli metin={formatTurkishDate(ann["Yayın Tarihi"])} /></span>
                </span>
              }
            >
              <div className="announcements-detail">
                <p className="announcements-detail__text">{getAnnouncementDetail(ann)}</p>
                {ann["Ekleri"] && ann["Ekleri"] !== '-' && (
                  <p className="announcements-detail__attach">
                    Ek: {ann["Ekleri"]}
                  </p>
                )}
                {(ann.ekler?.length ?? 0) > 0 ? (
                  <ul className="announcements-detail__ekler">
                    {ann.ekler!.map((ek, j) => (
                      <li key={ek.id ?? `${j}-${ek.url}`}><EkBaglantisi ek={ek} /></li>
                    ))}
                  </ul>
                ) : ann["Ekleri_url"] && (
                  // B58: a link that leaves the page says so with Carbon's Launch icon.
                  <Link href={ann["Ekleri_url"]} target="_blank" rel="noopener noreferrer" renderIcon={Launch}>
                    Eki aç
                  </Link>
                )}
              </div>
            </AccordionItem>
          )
        })}
      </Accordion>
    </div>
  )
}
