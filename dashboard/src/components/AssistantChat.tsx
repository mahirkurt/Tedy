import './AssistantChat.scss'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  AILabel,
  Button,
  IconButton,
  InlineLoading,
  SkeletonText,
  Tag,
  TextArea,
  Tile,
} from '@carbon/react'
import {
  Send,
  CalendarHeatMap,
  Chemistry,
  TaskComplete,
  ParentChild,
  Renew,
  Copy,
  Search,
  Time,
} from '@carbon/icons-react'
import type { AssistantCitation, AssistantPlanBlock, AssistantResponse } from '../types'
import { renderMarkdown } from '../utils/markdown'
import CitationChip from './CitationChip'
import SourcePanel from './SourcePanel'

type ChatRole = 'user' | 'assistant'

interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  citations?: AssistantCitation[]
  safetyFlags?: string[]
  planBlocks?: AssistantPlanBlock[]
  degraded?: string[]
}

const QUICK_PROMPTS = [
  { text: 'Çalışma planı hazırla', icon: CalendarHeatMap, mode: 'plan' as const },
  { text: 'Eksik konularımı özetle', icon: Chemistry, mode: 'chat' as const },
  { text: 'Bugün neye öncelik vermeliyim?', icon: TaskComplete, mode: 'chat' as const },
  { text: 'Veli kontrol listesi üret', icon: ParentChild, mode: 'chat' as const },
]

const WAITING_MESSAGES = [
  'Veriler analiz ediliyor...',
  'Kaynaklar taranıyor...',
  'Yanıt hazırlanıyor...',
  'Neredeyse bitti...',
]

function toApiMessages(messages: ChatMessage[]) {
  return messages.map(m => ({ role: m.role, content: m.content }))
}

/** The user turn that produced a given assistant message, if any. */
function promptBehind(msgs: ChatMessage[], assistantId: string): string | null {
  const idx = msgs.findIndex(m => m.id === assistantId)
  if (idx < 0) return null
  for (let i = idx - 1; i >= 0; i -= 1) {
    if (msgs[i].role === 'user') return msgs[i].content
  }
  return null
}

// Severity split for safety_flags (Task 6's measured outcome): `risk:*` is a
// genuine escalation and stays red; `warning:*` is informational (e.g. the
// tool-free, source-free "merhaba" case) and must not compete visually with
// a real crisis flag. Only the two known warning tokens get a friendly
// Turkish label — an unrecognised flag prints raw rather than being
// silently swallowed.
const FLAG_LABELS: Record<string, string> = {
  'warning:limited_confidence': 'Kaynaksız cevap',
  'warning:stale_context': 'Veriler güncel olmayabilir',
}

function flagTone(f: string): 'red' | 'gray' {
  return f.startsWith('risk:') ? 'red' : 'gray'
}

// `meta.degraded` is a list, not a flag — every server named in it failed
// independently and each one is a separate fact the reader is owed. Folding
// the list into a single badge (as Task 10 shipped it) silently drops every
// server past the first. Known servers get a friendly Turkish label; an
// unrecognised server id surfaces by its own name rather than vanishing
// behind the known one's message.
const DEGRADED_LABELS: Record<string, string> = {
  'maarif-mufredat': 'Müfredat kaynağına ulaşılamadı',
  'egitim-kaynak': 'Açık eğitim kaynağına ulaşılamadı',
}

function degradedLabel(server: string): string {
  return DEGRADED_LABELS[server] ?? `Kaynağa ulaşılamadı: ${server}`
}

async function parseJsonSafe(res: Response): Promise<AssistantResponse | { error?: string }> {
  const raw = await res.text()
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    try {
      return JSON.parse(raw) as AssistantResponse | { error?: string }
    } catch {
      return { error: `Geçersiz JSON yanıtı (HTTP ${res.status})` }
    }
  }
  const preview = raw.replace(/\s+/g, ' ').slice(0, 180)
  return { error: `Sunucu JSON dönmedi (HTTP ${res.status}): ${preview || 'boş yanıt'}` }
}

function ThinkingIndicator() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Advance one message every six seconds — derived from elapsed, not mirrored
  // into a second piece of state.
  const msgIdx = Math.min(Math.floor(elapsed / 6), WAITING_MESSAGES.length - 1)

  return (
    <article className="ac-msg ac-msg--assistant ac-msg--thinking">
      <div className="ac-msg__avatar ac-msg__avatar--ai">
        <AILabel size="mini" />
      </div>
      <div className="ac-msg__body">
        <div className="ac-msg__thinking-row">
          <InlineLoading description={WAITING_MESSAGES[msgIdx]} />
          {elapsed > 2 && (
            <span className="ac-msg__elapsed">{elapsed}s</span>
          )}
        </div>
        <SkeletonText paragraph lineCount={3} />
      </div>
    </article>
  )
}

function AnswerBody({
  text,
  citations,
  onActivate,
}: {
  text: string
  citations: AssistantCitation[]
  onActivate: (id: string) => void
}) {
  const byId = useMemo(
    () => new Map(citations.map(c => [c.id, c])),
    [citations],
  )

  return (
    <>
      {renderMarkdown(text, {
        renderToken: (token, key) => {
          const citation = byId.get(token.slice(1, -1))
          // A marker the backend could not resolve should not have survived,
          // but if one does, show its text rather than swallowing it.
          if (!citation) return <span key={key}>{token}</span>
          return <CitationChip key={key} citation={citation} onActivate={onActivate} />
        },
      })}
    </>
  )
}

export default function AssistantChat() {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Merhaba! TEDY Asistan olarak sana yardımcı olabilirim. Ödevlerin, sınavların ve derslerin hakkında sorular sorabilir veya kişisel çalışma planı isteyebilirsin.',
    },
  ])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeCitation, setActiveCitation] = useState<string | null>(null)

  const latestAssistant = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'assistant') return messages[i]
    }
    return null
  }, [messages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function submit(mode: 'chat' | 'plan', forcedPrompt?: string, opts?: { deep?: boolean }) {
    const content = (forcedPrompt ?? draft).trim()
    if (!content || loading) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    }

    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setDraft('')
    setLoading(true)
    setError(null)

    try {
      const endpoint = mode === 'plan' ? '/api/assistant/plan' : '/api/assistant/chat'
      const res = await fetch(endpoint, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'dashboard-default',
          context_filters: {},
          messages: toApiMessages(nextMessages),
          ...(opts?.deep ? { force_deep: true } : {}),
        }),
      })

      const payload = await parseJsonSafe(res)
      if (!res.ok) {
        throw new Error((payload as { error?: string }).error || `HTTP ${res.status}`)
      }

      const out = payload as AssistantResponse
      const answer = (out.answer || '').trim() || 'Yanıt üretilemedi.'
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: answer,
        citations: out.citations || [],
        safetyFlags: out.safety_flags || [],
        planBlocks: out.plan_blocks || [],
        degraded: out.meta?.degraded || [],
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Asistan hatası')
    } finally {
      setLoading(false)
    }
  }

  function regenerate(assistantId: string) {
    const prompt = promptBehind(messages, assistantId)
    if (!prompt) return
    // Drop the answer being replaced so the new one does not read as a second
    // reply to the same question.
    setMessages(prev => prev.filter(m => m.id !== assistantId))
    void submit('chat', prompt)
  }

  function deepen(assistantId: string) {
    const prompt = promptBehind(messages, assistantId)
    if (prompt) void submit('chat', prompt, { deep: true })
  }

  function activateCitation(id: string) {
    setActiveCitation(id)
  }

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    void submit('chat')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void submit('chat')
    }
  }

  const hasPlanBlocks = latestAssistant?.planBlocks && latestAssistant.planBlocks.length > 0

  return (
    <section className="ac">
      {/* Header */}
      <header className="ac__header">
        <div className="ac__header-left">
          <AILabel size="xl" />
          <div>
            <h2 className="ac__title">TEDY Asistan</h2>
            <p className="ac__subtitle">Kaynaklı soru-cevap ve kişisel çalışma planı</p>
          </div>
        </div>
      </header>

      {/* Quick prompts */}
      <div className="ac__prompts">
        {QUICK_PROMPTS.map(qp => (
          <button
            key={qp.text}
            type="button"
            className="ac__prompt-chip"
            onClick={() => void submit(qp.mode, qp.text)}
            disabled={loading}
          >
            <qp.icon size={16} />
            {qp.text}
          </button>
        ))}
      </div>

      <div className="ac__layout">
        {/* Chat panel */}
        <div className="ac__chat">
          <div className="ac__messages">
            {messages.map(msg => (
              <article key={msg.id} className={`ac-msg ac-msg--${msg.role}`}>
                <div className={`ac-msg__avatar ${msg.role === 'assistant' ? 'ac-msg__avatar--ai' : 'ac-msg__avatar--user'}`}>
                  {msg.role === 'assistant' ? <AILabel size="mini" /> : <span>I</span>}
                </div>
                <div className="ac-msg__body">
                  {msg.degraded && msg.degraded.length > 0 && (
                    <div className="ac-msg__degraded">
                      {msg.degraded.map(server => (
                        <Tag key={server} type="gray" size="sm">
                          {degradedLabel(server)}
                        </Tag>
                      ))}
                    </div>
                  )}
                  <span className="ac-msg__role">
                    {msg.role === 'user' ? 'Işık' : 'Asistan'}
                  </span>
                  <div className="ac-msg__content">
                    {msg.role === 'assistant'
                      ? <AnswerBody text={msg.content} citations={msg.citations ?? []} onActivate={activateCitation} />
                      : msg.content}
                  </div>
                  {msg.safetyFlags && msg.safetyFlags.length > 0 && (
                    <div className="ac-msg__flags">
                      {msg.safetyFlags.map(f => (
                        <Tag key={f} type={flagTone(f)} size="sm">{FLAG_LABELS[f] ?? f}</Tag>
                      ))}
                    </div>
                  )}
                  {msg.role === 'assistant' && msg.id !== 'welcome' && (
                    <div className="ac-msg__actions">
                      <IconButton kind="ghost" size="sm" label="Kopyala"
                        onClick={() => void navigator.clipboard.writeText(msg.content)}>
                        <Copy />
                      </IconButton>
                      <IconButton kind="ghost" size="sm" label="Yeniden üret"
                        onClick={() => void regenerate(msg.id)}>
                        <Renew />
                      </IconButton>
                      <Button kind="ghost" size="sm" renderIcon={Search}
                        onClick={() => deepen(msg.id)}>
                        Daha derine in
                      </Button>
                    </div>
                  )}
                </div>
              </article>
            ))}

            {loading && <ThinkingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {/* Composer */}
          <form className="ac__composer" onSubmit={onSubmit}>
            <div className="ac__input-row">
              <TextArea
                ref={textareaRef}
                id="ac-input"
                labelText=""
                hideLabel
                value={draft}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder={loading ? 'Yanıt bekleniyor...' : 'Bir soru sor veya çalışma planı iste...'}
                disabled={loading}
                className="ac__textarea"
              />
              <div className="ac__send-group">
                <IconButton
                  kind="primary"
                  label="Gönder"
                  size="lg"
                  disabled={loading || !draft.trim()}
                  type="submit"
                >
                  <Send />
                </IconButton>
                <IconButton
                  kind="ghost"
                  label="Çalışma Planı"
                  size="lg"
                  disabled={loading || !draft.trim()}
                  onClick={() => void submit('plan')}
                >
                  <CalendarHeatMap />
                </IconButton>
              </div>
            </div>
            {error && (
              <div className="ac__error">
                <Tag type="red" size="sm">{error}</Tag>
                <Button
                  kind="ghost"
                  size="sm"
                  renderIcon={Renew}
                  onClick={() => {
                    setError(null)
                    const lastUser = [...messages].reverse().find(m => m.role === 'user')
                    if (lastUser) void submit('chat', lastUser.content)
                  }}
                >
                  Tekrar dene
                </Button>
              </div>
            )}
          </form>
        </div>

        {/* Side panels */}
        <aside className="ac__side">
          <SourcePanel citations={latestAssistant?.citations ?? []} activeId={activeCitation} />

          <Tile className="ac__panel">
            <h4 className="ac__panel-title">
              <Time size={16} /> Plan Blokları
            </h4>
            {hasPlanBlocks ? (
              <ul className="ac__ref-list">
                {latestAssistant!.planBlocks!.map((b, idx) => (
                  <li key={`${b.day}-${idx}`} className="ac__plan-item">
                    <div className="ac__plan-header">
                      <Tag type="blue" size="sm">{b.day}</Tag>
                      <span className="ac__plan-time">{b.estimated_minutes} dk</span>
                    </div>
                    <span className="ac__plan-title">{b.title}</span>
                    <p className="ac__plan-actions">{b.actions.join(' \u2022 ')}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ac__muted">Çalışma planı oluşturulduğunda burada görünecek.</p>
            )}
          </Tile>
        </aside>
      </div>
    </section>
  )
}
