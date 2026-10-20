import { useCallback, useEffect, useRef, useState } from 'react'
import { InlineNotification, SkeletonText } from '@carbon/react'
import type { ModuleTicket } from '../types'
import {
  acceptProgressMessage, acceptSizeMessage, appearanceMessage, DASHBOARD_THEME, restoreMessage, type RestoreState,
} from '../utils/moduleBridge'
import ModulAiEtiketi from './ModulAiEtiketi'
import { useModulAciklamasi } from '../hooks/useModulAciklamasi'
import ModulBasligi from './ModulBasligi'
import './Modules.scss'

// The dashboard's computed root font size. The frame is a separate document, so it does not
// inherit the host's clamp() and cannot derive the scale itself: inside the frame `100vw` is the
// frame's width (the column minus the page padding), which would couple module type size to
// dashboard layout and mis-scale a standalone module. So the host reports the value (spec §10.2).
const kokPx = () => parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
// The band and the bottom bar are kept clear by the page's scroll-padding (ted-theme.scss); a
// frame top inside it is as hidden as one above the viewport.
const ustBosluk = () => parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0

type TicketState = { status: 'loading' } | { status: 'ready'; url: string } | { status: 'error'; message: string }

const TICKET_ERRORS: Record<number, string> = {
  403: 'Bu modülü açma yetkin yok.',
  404: 'Modül bulunamadı; kaldırılmış olabilir.',
  503: 'Modül görüntüleyici henüz yapılandırılmadı.',
}

export interface ModuleViewerProps {
  ticketPath: string
  title: string
  /** What the frame's AI label explains (talimatname S41, B71). */
  aciklamaPath: string
  /** Absent for draft previews: a draft never writes progress. */
  progress?: { slug: string; version: number }
  /** Shown between the head and the frame (the draft preview's notice). */
  ust?: React.ReactNode
}

export default function ModuleViewer({ ticketPath, title, aciklamaPath, progress, ust }: ModuleViewerProps) {
  const frameRef = useRef<HTMLIFrameElement>(null)
  const aciklama = useModulAciklamasi(aciklamaPath)
  const bas = <ModulBasligi durum={aciklama} taslak={!progress} aiEtiketi={<ModulAiEtiketi durum={aciklama} />} />
  // Reset to loading during render when ticketPath changes, rather than with a
  // synchronous setState at the top of the effect below (React's "adjusting
  // state when a prop changes" pattern) — the fetch itself still runs in the effect.
  const [seenTicketPath, setSeenTicketPath] = useState(ticketPath)
  const [ticket, setTicket] = useState<TicketState>({ status: 'loading' })
  const [saveFailed, setSaveFailed] = useState(false)
  // The module's content height once it reports one (flow layout). Until then — and for a module
  // compiled before the flow layout existed — the frame keeps its fixed minimum and its own scroll.
  const [yukseklik, setYukseklik] = useState<number | null>(null)
  const slug = progress?.slug
  const version = progress?.version

  if (seenTicketPath !== ticketPath) {
    setSeenTicketPath(ticketPath)
    setTicket({ status: 'loading' })
    setYukseklik(null)
  }

  useEffect(() => {
    let cancelled = false
    fetch(ticketPath, { credentials: 'include' })
      .then(async res => {
        if (!res.ok) throw new Error(TICKET_ERRORS[res.status] ?? 'Modül şu an açılamadı. Birkaç dakika sonra yeniden dene.')
        const body = (await res.json()) as ModuleTicket
        if (!cancelled) setTicket({ status: 'ready', url: body.url })
      })
      .catch((e: unknown) => {
        // B43 (D4): only our own sentences reach the page; a network failure's text ("Failed to fetch") does not.
        const bizim = e instanceof Error && Object.values(TICKET_ERRORS).concat('Modül şu an açılamadı. Birkaç dakika sonra yeniden dene.').includes(e.message)
        if (!cancelled) setTicket({ status: 'error', message: bizim ? (e as Error).message : 'Modül açılamadı. Bağlantını kontrol edip yeniden dene.' })
      })
    return () => { cancelled = true }
  }, [ticketPath])

  const onMessage = useCallback((event: MessageEvent) => {
    const frameEl = frameRef.current
    const boy = acceptSizeMessage(event, frameEl?.contentWindow ?? null)
    if (boy) {
      setYukseklik(boy.height)
      // A section change: the module scrolls its own window to the top, which in a frame without
      // a scroll of its own moves nothing — so the page brings the frame's top into view, and only
      // when the reader has scrolled past it (opening a module never moves the page).
      if (boy.top && frameEl && frameEl.getBoundingClientRect().top < ustBosluk()) {
        frameEl.scrollIntoView({ block: 'start' })
      }
      return
    }
    if (!slug || !version) return
    const frame = frameEl?.contentWindow ?? null
    const message = acceptProgressMessage(event, frame, slug, version)
    if (!message || !frame) return
    if (message.event === 'ready') {
      fetch(`/api/modules/${slug}/progress?version=${version}`, { credentials: 'include' })
        .then(res => (res.ok ? res.json() : null))
        .then((body: { state?: RestoreState } | null) => {
          // The sandboxed frame has an opaque origin, so '*' is the only target that reaches it;
          // the window reference, not the origin string, is what addresses this exact frame.
          if (body?.state) frame.postMessage(restoreMessage(body.state), '*')
        })
        .catch(() => setSaveFailed(true))
      return
    }
    fetch(`/api/modules/${slug}/progress`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message),
    })
      .then(res => { if (!res.ok) setSaveFailed(true) })
      .catch(() => setSaveFailed(true))
  }, [slug, version])

  useEffect(() => {
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [onMessage])

  // On load (drafts included — they send no 'ready'), tell the module which Carbon theme the
  // dashboard renders in, at what root font size, and that it sits in the page's flow — so the two
  // read as one surface. As with restore, '*' is the only target that reaches the opaque-origin
  // frame; the contentWindow reference addresses it.
  const gonderGorunum = useCallback(() => {
    frameRef.current?.contentWindow?.postMessage(appearanceMessage(DASHBOARD_THEME, kokPx(), 'flow'), '*')
  }, [])
  const onFrameLoad = gonderGorunum

  // Above 1920px the dashboard's root font size grows with the window (ted-theme.scss clamp), so
  // a resize changes it. Re-announce only when the value actually changed: an unchanged resend
  // would make the module rewrite its root font size on every resize frame.
  useEffect(() => {
    let son = kokPx()
    let bekleyen = 0
    const olcVeGonder = () => {
      bekleyen = 0
      const simdi = kokPx()
      if (simdi !== son) { son = simdi; gonderGorunum() }
    }
    const onResize = () => { if (!bekleyen) bekleyen = requestAnimationFrame(olcVeGonder) }
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      if (bekleyen) cancelAnimationFrame(bekleyen)
    }
  }, [gonderGorunum])

  if (ticket.status === 'loading') {
    return <div className="module-viewer">{bas}{ust}<div aria-busy="true"><SkeletonText paragraph lineCount={3} /></div></div>
  }
  if (ticket.status === 'error') {
    return (
      <div className="module-viewer">
        {bas}{ust}
        <InlineNotification kind="error" role="alert" lowContrast hideCloseButton statusIconDescription="Hata" title="Modül açılamadı" subtitle={ticket.message} />
      </div>
    )
  }
  return (
    <div className="module-viewer">
      {bas}
      {ust}
      {saveFailed && (
        <InlineNotification kind="warning" lowContrast hideCloseButton statusIconDescription="Uyarı" title="İlerleme kaydedilemedi"
          subtitle="Modül çalışmaya devam ediyor; sayfayı yenileyince kayıt yeniden denenir." />
      )}
      <iframe ref={frameRef} className={yukseklik ? 'module-frame module-frame--akis' : 'module-frame'}
        style={yukseklik ? { height: yukseklik } : undefined} scrolling={yukseklik ? 'no' : undefined}
        title={title} src={ticket.url} sandbox="allow-scripts" referrerPolicy="no-referrer" onLoad={onFrameLoad} />
    </div>
  )
}
