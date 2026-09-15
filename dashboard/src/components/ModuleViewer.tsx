import { useCallback, useEffect, useRef, useState } from 'react'
import { InlineNotification, SkeletonText } from '@carbon/react'
import type { ModuleTicket } from '../types'
import { acceptProgressMessage, restoreMessage, type RestoreState } from '../utils/moduleBridge'
import './Modules.scss'

type TicketState = { status: 'loading' } | { status: 'ready'; url: string } | { status: 'error'; message: string }

const TICKET_ERRORS: Record<number, string> = {
  403: 'Bu modülü açma yetkin yok.',
  404: 'Modül bulunamadı; kaldırılmış olabilir.',
  503: 'Modül görüntüleyici henüz yapılandırılmadı.',
}

export interface ModuleViewerProps {
  ticketPath: string
  title: string
  /** Absent for draft previews: a draft never writes progress. */
  progress?: { slug: string; version: number }
}

export default function ModuleViewer({ ticketPath, title, progress }: ModuleViewerProps) {
  const frameRef = useRef<HTMLIFrameElement>(null)
  // Reset to loading during render when ticketPath changes, rather than with a
  // synchronous setState at the top of the effect below (React's "adjusting
  // state when a prop changes" pattern) — the fetch itself still runs in the effect.
  const [seenTicketPath, setSeenTicketPath] = useState(ticketPath)
  const [ticket, setTicket] = useState<TicketState>({ status: 'loading' })
  const [saveFailed, setSaveFailed] = useState(false)
  const slug = progress?.slug
  const version = progress?.version

  if (seenTicketPath !== ticketPath) {
    setSeenTicketPath(ticketPath)
    setTicket({ status: 'loading' })
  }

  useEffect(() => {
    let cancelled = false
    fetch(ticketPath, { credentials: 'include' })
      .then(async res => {
        if (!res.ok) throw new Error(TICKET_ERRORS[res.status] ?? `Modül açılamadı (HTTP ${res.status}).`)
        const body = (await res.json()) as ModuleTicket
        if (!cancelled) setTicket({ status: 'ready', url: body.url })
      })
      .catch((e: unknown) => {
        if (!cancelled) setTicket({ status: 'error', message: e instanceof Error ? e.message : 'Modül açılamadı.' })
      })
    return () => { cancelled = true }
  }, [ticketPath])

  const onMessage = useCallback((event: MessageEvent) => {
    if (!slug || !version) return
    const frame = frameRef.current?.contentWindow ?? null
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

  if (ticket.status === 'loading') {
    return <div className="module-viewer"><SkeletonText paragraph lineCount={3} /></div>
  }
  if (ticket.status === 'error') {
    return (
      <div className="module-viewer">
        <InlineNotification kind="error" lowContrast hideCloseButton title="Modül açılamadı" subtitle={ticket.message} />
      </div>
    )
  }
  return (
    <div className="module-viewer">
      {saveFailed && (
        <InlineNotification kind="warning" lowContrast hideCloseButton title="İlerleme kaydedilemedi"
          subtitle="Modül çalışmaya devam ediyor; sayfayı yenileyince kayıt yeniden denenir." />
      )}
      <iframe ref={frameRef} className="module-frame" title={title} src={ticket.url}
        sandbox="allow-scripts" referrerPolicy="no-referrer" />
    </div>
  )
}
