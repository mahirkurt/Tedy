import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
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
  'Bu hafta ödev ve sınavlara göre çalışma planı hazırla.',
  'Fen Bilimleri için veriye dayalı eksik konularımı özetle.',
  'Ödev teslim tarihine göre bugün neye öncelik vermeliyim?',
  'Veli için 5 maddelik akşam kontrol listesi üret.',
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

export default function AssistantChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Merhaba, TEDY Asistan hazır. Soru sorabilir veya çalışma planı isteyebilirsin.',
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

  return (
    <section className="assistant-page">
      <header className="assistant-page__header">
        <h2 className="assistant-page__title">Asistan</h2>
        <p className="assistant-page__subtitle">
          Kaynaklı soru-cevap ve kişiselleştirilmiş çalışma planı
        </p>
      </header>

      <div className="assistant-page__quick-prompts" aria-label="Hızlı sorular">
        {QUICK_PROMPTS.map(prompt => (
          <button
            key={prompt}
            type="button"
            className="assistant-page__quick-btn"
            onClick={() => {
              void submit('chat', prompt)
            }}
            disabled={loading}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="assistant-page__layout">
        <div className="assistant-page__chat">
          <div className="assistant-page__messages">
            {messages.map(msg => (
              <article
                key={msg.id}
                className={`assistant-page__msg assistant-page__msg--${msg.role}`}
              >
                <p className="assistant-page__msg-role">
                  {msg.role === 'user' ? 'Sen' : 'Asistan'}
                </p>
                <p className="assistant-page__msg-content">{msg.content}</p>
                {msg.safetyFlags && msg.safetyFlags.length > 0 && (
                  <p className="assistant-page__msg-flags">
                    Güvenlik: {msg.safetyFlags.join(', ')}
                  </p>
                )}
              </article>
            ))}
          </div>

          <form className="assistant-page__composer" onSubmit={onSubmit}>
            <textarea
              value={draft}
              onChange={e => setDraft(e.target.value)}
              rows={4}
              placeholder="Sorunu yaz..."
              className="assistant-page__input"
              disabled={loading}
            />
            <div className="assistant-page__actions">
              <button type="submit" disabled={loading || !draft.trim()} className="assistant-page__action-btn">
                {loading ? 'Yanıtlanıyor...' : 'Sor'}
              </button>
              <button
                type="button"
                disabled={loading || !draft.trim()}
                className="assistant-page__action-btn assistant-page__action-btn--secondary"
                onClick={() => {
                  void submit('plan')
                }}
              >
                Çalışma Planı Oluştur
              </button>
            </div>
            {error && <p className="assistant-page__error">{error}</p>}
          </form>
        </div>

        <aside className="assistant-page__side">
          <section className="assistant-page__panel">
            <h3>Kaynaklar</h3>
            {latestAssistant?.citations && latestAssistant.citations.length > 0 ? (
              <ul className="assistant-page__list">
                {latestAssistant.citations.map(c => (
                  <li key={c.id}>
                    <p className="assistant-page__list-title">{c.id} • {c.path}</p>
                    <p className="assistant-page__list-snippet">{c.snippet}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="assistant-page__muted">Henüz kaynak bulunmuyor.</p>
            )}
          </section>

          <section className="assistant-page__panel">
            <h3>Plan Blokları</h3>
            {latestAssistant?.planBlocks && latestAssistant.planBlocks.length > 0 ? (
              <ul className="assistant-page__list">
                {latestAssistant.planBlocks.map((b, idx) => (
                  <li key={`${b.day}-${idx}`}>
                    <p className="assistant-page__list-title">{b.day} • {b.title}</p>
                    <p className="assistant-page__list-snippet">
                      {b.estimated_minutes} dk • {b.actions.join(' | ')}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="assistant-page__muted">Plan oluşturulduğunda burada görünecek.</p>
            )}
          </section>
        </aside>
      </div>
    </section>
  )
}
