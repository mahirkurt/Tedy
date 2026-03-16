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
  DocumentView,
  Time,
} from '@carbon/icons-react'
import type { AssistantCitation, AssistantPlanBlock, AssistantResponse } from '../types'

type ChatRole = 'user' | 'assistant'

interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  citations?: AssistantCitation[]
  safetyFlags?: string[]
  planBlocks?: AssistantPlanBlock[]
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
  const [msgIdx, setMsgIdx] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (elapsed > 0 && elapsed % 6 === 0) {
      setMsgIdx(prev => Math.min(prev + 1, WAITING_MESSAGES.length - 1))
    }
  }, [elapsed])

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

  const latestAssistant = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'assistant') return messages[i]
    }
    return null
  }, [messages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function submit(mode: 'chat' | 'plan', forcedPrompt?: string) {
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
        }),
      })

      const payload = await parseJsonSafe(res)
      if (!res.ok) {
        throw new Error((payload as { error?: string }).error || `HTTP ${res.status}`)
      }

      const out = payload as AssistantResponse
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: out.answer || 'Yanıt üretilemedi.',
        citations: out.citations || [],
        safetyFlags: out.safety_flags || [],
        planBlocks: out.plan_blocks || [],
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Asistan hatası')
    } finally {
      setLoading(false)
    }
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

  const hasCitations = latestAssistant?.citations && latestAssistant.citations.length > 0
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
                  <span className="ac-msg__role">
                    {msg.role === 'user' ? 'Işık' : 'Asistan'}
                  </span>
                  <p className="ac-msg__content">{msg.content}</p>
                  {msg.safetyFlags && msg.safetyFlags.length > 0 && (
                    <div className="ac-msg__flags">
                      {msg.safetyFlags.map(f => (
                        <Tag key={f} type="red" size="sm">{f}</Tag>
                      ))}
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
          <Tile className="ac__panel">
            <h4 className="ac__panel-title">
              <DocumentView size={16} /> Kaynaklar
            </h4>
            {hasCitations ? (
              <ul className="ac__ref-list">
                {latestAssistant!.citations!.map(c => (
                  <li key={c.id} className="ac__ref-item">
                    <span className="ac__ref-path">{c.path}</span>
                    <p className="ac__ref-snippet">{c.snippet}</p>
                    {c.confidence > 0 && (
                      <Tag type={c.confidence >= 0.7 ? 'green' : c.confidence >= 0.4 ? 'blue' : 'gray'} size="sm">
                        {Math.round(c.confidence * 100)}%
                      </Tag>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ac__muted">Soru sorduğunda kaynaklar burada görünecek.</p>
            )}
          </Tile>

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
