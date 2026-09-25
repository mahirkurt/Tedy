import './AssistantChat.scss'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  AILabel,
  AILabelContent,
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
  Renew,
  Copy,
  Search,
  Time,
} from '@carbon/icons-react'
import type { AssistantCitation, AssistantPlanBlock, AssistantResponse } from '../types'
import { renderMarkdown } from '../utils/markdown'
import { modelAdi } from '../utils/formatters'
import { firstName, useSession } from '../contexts/session'
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
  /** Which model produced this answer. The backend cycles through a chain,
   *  so this is not a constant and Carbon's AI guidance asks that it be
   *  disclosed rather than implied. */
  model?: string
}

// The page speaks to whoever is signed in, as the model does (the prompt's
// "## Hitap"): "sen" to Işık, "siz" to the family, who hear about Işık in the
// third person. One voice per reader (İ9) — a parent's question labelled
// "Işık", under a greeting written to Işık, was two voices at once.
const VOICE = {
  student: {
    welcome: 'Merhaba! TEDY Asistan olarak sana yardımcı olabilirim. Ödevlerin, sınavların ve derslerin hakkında sorular sorabilir veya kişisel çalışma planı isteyebilirsin.',
    prompts: [
      { text: 'Bugün neye öncelik vermeliyim?', icon: TaskComplete, mode: 'chat' as const, primary: true },
      { text: 'Çalışma planı hazırla', icon: CalendarHeatMap, mode: 'plan' as const },
      { text: 'Eksik konularımı özetle', icon: Chemistry, mode: 'chat' as const },
    ],
    placeholder: 'Bir soru sor veya çalışma planı iste...',
    sources: 'Her iddianın yanındaki numara, o cümlenin nereden geldiğini gösterir — MEB müfredatı, ders kitabın veya kendi okul verin. Numaraya dokunup kaynağı okuyabilirsin.',
    caution: 'Yapay zekâ yanılabilir. Bir şey tuhaf geldiyse kaynağa bak.',
  },
  family: {
    welcome: "Merhaba! TEDY Asistan olarak size yardımcı olabilirim. Işık'ın ödevleri, sınavları ve dersleri hakkında soru sorabilir veya onun için çalışma planı isteyebilirsiniz.",
    prompts: [
      { text: 'Işık bugün neye öncelik vermeli?', icon: TaskComplete, mode: 'chat' as const, primary: true },
      { text: 'Işık için çalışma planı hazırla', icon: CalendarHeatMap, mode: 'plan' as const },
      { text: "Işık'ın eksik konularını özetle", icon: Chemistry, mode: 'chat' as const },
    ],
    placeholder: 'Bir soru sorun veya çalışma planı isteyin...',
    sources: "Her iddianın yanındaki numara, o cümlenin nereden geldiğini gösterir — MEB müfredatı, ders kitabı veya Işık'ın okul verisi. Numaraya dokunup kaynağı okuyabilirsiniz.",
    caution: 'Yapay zekâ yanılabilir. Bir şey tuhaf geldiyse kaynağa bakın.',
  },
}

// Shown in the composer while a tool is running, keyed by the tool name the
// stream endpoint reports in its `tool_start` event. Anything not in this map
// (a tool added on the backend without a matching label here) still shows a
// generic fallback rather than a blank or raw tool id.
const TOOL_LABEL: Record<string, string> = {
  ogrenci_verisi_ara: 'Okul verilerin taranıyor',
  kazanim_ara: 'MEB kazanımları aranıyor',
  kazanim_listele: 'Kazanım listesi alınıyor',
  mufredat_ara: 'Müfredat aranıyor',
  kitap_listele: 'Ders kitapları listeleniyor',
  kitap_sayfa: 'Ders kitabı sayfası okunuyor',
  figur_ara: 'Görsel aranıyor',
  figur_getir: 'Görsel getiriliyor',
  oer_ara: 'Açık kaynaklar taranıyor',
  oer_kazanima_gore: 'Kazanıma bağlı kaynaklar alınıyor',
  modul_ara: 'Yayınlanmış modüller aranıyor',
  odev_listesi: 'Ödev listen okunuyor',
}

const DEFAULT_THINKING_MESSAGE = 'Yanıt hazırlanıyor...'

/** Read an SSE body and hand each event to the caller. */
async function readEventStream(
  res: Response,
  onEvent: (name: string, data: Record<string, unknown>) => void,
): Promise<void> {
  const reader = res.body?.getReader()
  if (!reader) throw new Error('akış gövdesi yok')
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // Frames are separated by a blank line; keep the trailing partial frame.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      let name = 'message'
      let payload = '{}'
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) name = line.slice(7).trim()
        else if (line.startsWith('data: ')) payload = line.slice(6)
      }
      try {
        onEvent(name, JSON.parse(payload))
      } catch {
        // A malformed frame must not kill the stream.
      }
    }
  }
}

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
  'error:model_unavailable': 'Asistana ulaşılamadı',
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
  'modul-katalogu': 'Modül kataloğu okunamadı',
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

function ThinkingIndicator({ stage }: { stage: string | null }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <article className="ac-msg ac-msg--assistant ac-msg--thinking">
      <div className="ac-msg__avatar ac-msg__avatar--ai">
        <AILabel size="mini" slugLabel="yanıtı" aria-label="Yapay zekâ yanıtı" />
      </div>
      <div className="ac-msg__body">
        <div className="ac-msg__thinking-row">
          <InlineLoading description={stage ?? DEFAULT_THINKING_MESSAGE} />
          {elapsed > 2 && (
            <span className="ac-msg__elapsed">{elapsed}s</span>
          )}
        </div>
        <SkeletonText paragraph lineCount={3} />
      </div>
    </article>
  )
}

/** Citation markers hidden while the answer is being written: the sources
 * they point at arrive only with the final answer, and a bare "[S1]" is
 * internal representation (D4). A marker cut in half at the end of what has
 * arrived so far ("[S", "[S1") goes too. */
function taslakMetni(text: string): string {
  return text.replace(/\s?\[S\d+\]/g, '').replace(/\s?\[(S\d*)?$/, '')
}

/** The answer while it is written. It takes the thinking indicator's place:
 * words appearing is the visible-time cue, for a reader who loses a blank
 * seventeen-second wait. The final answer replaces it. */
function WritingAnswer({ text }: { text: string }) {
  return (
    <article className="ac-msg ac-msg--assistant ac-msg--writing" aria-busy="true">
      <div className="ac-msg__avatar ac-msg__avatar--ai">
        <AILabel size="mini" slugLabel="yanıtı" aria-label="Yapay zekâ yanıtı" />
      </div>
      <div className="ac-msg__body">
        <span className="ac-msg__role">Asistan</span>
        <div className="ac-msg__content">{renderMarkdown(taslakMetni(text))}</div>
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
  const user = useSession()
  const isStudent = user?.student === true
  const voice = isStudent ? VOICE.student : VOICE.family
  const askerName = isStudent ? 'Işık' : (firstName(user) || 'Siz')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([
    // Its text comes from `voice` at render time: the session can settle
    // after this state is created.
    { id: 'welcome', role: 'assistant', content: '' },
  ])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeCitation, setActiveCitation] = useState<string | null>(null)
  const [stage, setStage] = useState<string | null>(null)
  /** The answer as it streams in; empty when nothing is being written. */
  const [writing, setWriting] = useState('')
  const isWriting = writing !== ''

  const latestAssistant = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'assistant') return messages[i]
    }
    return null
  }, [messages])

  // Once when writing starts, not on every piece: following the text down
  // would pull the reader's eye along with it (İ6). The pane scrolls, never
  // the window: scrollIntoView moved every scrollable ancestor, so on a phone
  // opening Asistan slid the page past its own title and prompts.
  useEffect(() => {
    const pane = messagesEndRef.current?.parentElement
    if (pane) pane.scrollTop = pane.scrollHeight
  }, [messages, loading, isWriting])

  /** Appends one assistant turn to the transcript from an AssistantResponse
   * payload, whether it arrived via the stream's `answer` event or a classic
   * JSON response — both endpoints return the same shape, so this is the one
   * place that turns it into a ChatMessage. */
  function appendAssistantMessage(payload: AssistantResponse) {
    const answer = (payload.answer || '').trim() || 'Yanıt üretilemedi.'
    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: answer,
      citations: payload.citations || [],
      safetyFlags: payload.safety_flags || [],
      planBlocks: payload.plan_blocks || [],
      degraded: payload.meta?.degraded || [],
      model: payload.meta?.model,
    }
    setMessages(prev => [...prev, assistantMsg])
  }

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
    setStage(null)
    setWriting('')

    const requestBody = {
      session_id: 'dashboard-default',
      context_filters: {},
      messages: toApiMessages(nextMessages),
      ...(opts?.deep ? { force_deep: true } : {}),
    }

    // The streaming endpoint only narrates AssistantRuntime.chat() — a study
    // plan needs study_plan()'s own plan_blocks, which chat() never
    // produces, so a 'plan' submission goes straight to the classic
    // endpoint rather than through the stream-then-fallback path below.
    // Routing it through the stream would return HTTP 200 with a real
    // answer and an empty plan, which is a silent failure of the plan
    // feature — status green, feature dead.
    if (mode === 'plan') {
      try {
        const res = await fetch('/api/assistant/plan', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        })
        const payload = await parseJsonSafe(res)
        if (!res.ok || 'error' in payload) {
          throw new Error((payload as { error?: string }).error || `HTTP ${res.status}`)
        }
        appendAssistantMessage(payload as AssistantResponse)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Asistan hatası')
      } finally {
        setStage(null)
        setLoading(false)
      }
      return
    }

    try {
      const res = await fetch('/api/assistant/stream', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      if (!res.ok || !res.body) throw new Error(`akış açılamadı (${res.status})`)

      let answered = false
      await readEventStream(res, (name, data) => {
        if (name === 'tool_start') {
          setStage(TOOL_LABEL[String(data.name)] ?? 'Kaynaklar taranıyor')
        } else if (name === 'answer_delta') {
          const piece = String(data.text ?? '')
          setWriting(prev => prev + piece)
        } else if (name === 'answer_reset') {
          // What was written came before a tool call; it is not the answer.
          setWriting('')
        } else if (name === 'answer') {
          answered = true
          setWriting('')
          appendAssistantMessage(data.payload as AssistantResponse)
        } else if (name === 'error') {
          throw new Error(String(data.error ?? 'akış hatası'))
        }
      })
      if (!answered) throw new Error('akış yanıtsız kapandı')
    } catch (streamErr) {
      // The non-streaming endpoint stays in place precisely for this: a proxy
      // that buffers SSE, an older worker, or the stream failing mid-flight
      // must not cost the user an answer. This is reported to the console,
      // not surfaced via setError — the reader gets an answer either way, so
      // it is not an error from where they sit.
      console.warn('akış başarısız, klasik uca düşülüyor:', streamErr)
      // A half-written draft must not sit there looking like the answer.
      setWriting('')
      try {
        const res = await fetch('/api/assistant/chat', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        })
        const payload = await parseJsonSafe(res)
        if (!res.ok || 'error' in payload) {
          throw new Error((payload as { error?: string }).error || `HTTP ${res.status}`)
        }
        appendAssistantMessage(payload as AssistantResponse)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Asistan hatası')
      }
    } finally {
      setStage(null)
      setWriting('')
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
  const latestModel = latestAssistant?.model

  return (
    <section className="ac">
      {/* Header */}
      <header className="ac__header">
        <div className="ac__header-left">
          {/* Carbon for AI treats the mark as a claim that has to be
              explainable. This used to be a bare <AILabel/>: a badge saying
              "AI" that answered no question about what the AI was, which
              model wrote the answer, or why its claims can be checked. */}
          <AILabel
            size="xl"
            autoAlign
            aiText="AI"
            slugLabel="bilgisi"
            aria-label="Yapay zekâ hakkında bilgi"
            align="bottom-left"
          >
            <AILabelContent>
              <h4 className="ac__ai-pop-title">Bu yanıtları bir yapay zekâ yazıyor</h4>
              <p className="ac__ai-pop-body">{voice.sources}</p>
              <p className="ac__ai-pop-body">{voice.caution}</p>
              <p className="ac__ai-pop-meta">
                {latestModel ? `Son yanıtı ${modelAdi(latestModel)} yazdı.` : 'Henüz yanıt yok.'}
              </p>
            </AILabelContent>
          </AILabel>
          <div>
            <h2 className="ac__title">TEDY Asistan</h2>
            <p className="ac__subtitle">Kaynaklı soru-cevap ve kişisel çalışma planı</p>
          </div>
        </div>
      </header>

      {/* Quick prompts */}
      <div className="ac__prompts">
        {voice.prompts.map(qp => (
          <button
            key={qp.text}
            type="button"
            className={qp.primary ? 'ac__prompt-chip ac__prompt-chip--primary' : 'ac__prompt-chip'}
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
                  {msg.role === 'assistant' ? (
                    <AILabel size="mini" slugLabel="yanıtı" aria-label="Yapay zekâ yanıtı" />
                  ) : <span>{askerName.charAt(0).toLocaleUpperCase('tr-TR')}</span>}
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
                    {msg.role === 'user' ? askerName : 'Asistan'}
                  </span>
                  <div className="ac-msg__content">
                    {msg.role === 'assistant'
                      ? <AnswerBody text={msg.id === 'welcome' ? voice.welcome : msg.content}
                          citations={msg.citations ?? []} onActivate={activateCitation} />
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

            {loading && (isWriting
              ? <WritingAnswer text={writing} />
              : <ThinkingIndicator stage={stage} />)}
            <div ref={messagesEndRef} />
          </div>

          {/* Composer */}
          <form className="ac__composer" onSubmit={onSubmit}>
            <div className="ac__input-row">
              <TextArea
                ref={textareaRef}
                id="ac-input"
                labelText="Sorun"
                hideLabel
                value={draft}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder={loading ? 'Yanıt bekleniyor...' : voice.placeholder}
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
        <aside className="ac__side" aria-label="Kaynaklar ve çalışma planı">
          <SourcePanel citations={latestAssistant?.citations ?? []} activeId={activeCitation} />

          <Tile className="ac__panel">
            <h2 className="ac__panel-title">
              <Time size={16} /> Plan Blokları
            </h2>
            {hasPlanBlocks ? (
              <ul className="ac__ref-list">
                {latestAssistant!.planBlocks!.map((b, idx) => (
                  <li key={`${b.day}-${idx}`} className="ac__plan-item">
                    <div className="ac__plan-header">
                      <Tag type="gray" size="sm">{b.day}</Tag>
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
