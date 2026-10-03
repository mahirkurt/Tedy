import './AssistantChat.scss'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  AILabel,
  AILabelContent,
  Button,
  IconButton,
  InlineLoading,
  SkeletonText,
  Select,
  SelectItem,
  Tag,
  TextArea,
  Tile,
  Modal,
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
  Idea,
  Close,
  Microphone,
} from '@carbon/icons-react'
import type { AssistantCitation, AssistantPlanBlock, AssistantResponse, ModOnerisi as Oneri, Netlestirme } from '../types'
import { renderMarkdown } from '../utils/markdown'
import { modelAdi } from '../utils/formatters'
import { subjectClass } from '../utils/subject'
import { firstName, useSession } from '../contexts/session'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { GENEL, useOgretmen } from '../hooks/useOgretmen'
import { kayitliAtiflar, useSohbetler } from '../hooks/useSohbetler'
import SohbetListesi from './SohbetListesi'
import { useSes } from '../hooks/useSes'
import { okunacakMetin } from '../utils/ses'
import CitationChip from './CitationChip'
import ModOnerisi from './ModOnerisi'
import OgretmenSecici from './OgretmenSecici'
import SourcePanel from './SourcePanel'
import AlistirmaKarti, { type Alistirma } from './AlistirmaKarti'
import OdevOnayKarti, { type OdevOnerisi } from './OdevOnayKarti'
import NetlestirmeSecenekleri from './NetlestirmeSecenekleri'
import YuklemeAlani from './YuklemeAlani'
import YuklenenEk, { type Yukleme } from './YuklenenEk'

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
  /** A genel-mode answer's suggestion to switch teacher; shown as a button, never applied. */
  modOnerisi?: Oneri | null
  /** Upload ids copied onto a composer send. Other paths leave this off. */
  ekler?: string[]
  yuklemeler?: Yukleme[]
  alistirma?: Alistirma[]
  netlestirme?: Netlestirme | null
  odevOnerisi?: OdevOnerisi | null
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
    ogretmenHata: 'Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsin.',
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
    ogretmenHata: 'Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsiniz.',
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
  odev_belgesi: 'Ödev belgesi aranıyor',
  odev_tamamla: 'Eksik alan kaydediliyor',
  skill_kaynagi: 'Öğretmen notları açılıyor',
  mod_oner: 'Öğretmen önerisi hazırlanıyor',
  netlestir: 'Seçenekler hazırlanıyor',
  alistirma_hazirla: 'Alıştırma hazırlanıyor',
  odev_fotograftan: 'Fotoğraftaki ödev okunuyor',
  yuklenen_dosya_oku: 'Ek okunuyor',
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
      let data: Record<string, unknown>
      try { data = JSON.parse(payload) } catch { continue }
      onEvent(name, data)
    }
  }
}

function toApiMessages(messages: ChatMessage[]) {
  return messages.map(m => ({
    role: m.role,
    content: m.content,
    ...(m.ekler && m.ekler.length ? { ekler: m.ekler } : {}),
  }))
}

const TUR: Record<string, string> = {
  gorsel: 'Görsel',
  pdf: 'PDF',
  docx: 'Word',
  txt: 'Metin',
}

interface Cip {
  yerel: string
  ad: string
  tur?: string
  id?: string
  hata?: string
  yukleniyor?: boolean
  baglaniyor?: boolean
  baglandi?: boolean
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
        <div className="ac-msg__content ac-md">{renderMarkdown(taslakMetni(text), { bicim: 'sohbet' })}</div>
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
        bicim: 'sohbet',
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
  const okur = isStudent ? 'ogrenci' : 'aile'
  const ogretmen = useOgretmen(user?.email)
  const sohbet = useSohbetler(user?.email, isStudent)
  const saltOkunur = sohbet.secili?.salt === true
  const secili = ogretmen.secili
  // A teacher's greeting and quick prompts come from its skill; Genel keeps the page's own.
  const welcome = secili ? secili.karsilama[okur] : voice.welcome
  const prompts = secili
    ? secili.hizli_sorular[okur].map((text, i) => ({ text, icon: Idea, mode: 'chat' as const, primary: i === 0 }))
    : voice.prompts
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composerRef = useRef<HTMLFormElement>(null)
  const pendingRequest = useRef<{ mode: 'chat' | 'plan'; body: Record<string, unknown> } | null>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([
    // Its text comes from `voice` at render time: the session can settle
    // after this state is created.
    { id: 'welcome', role: 'assistant', content: '' },
  ])
  const [draft, setDraft] = useState('')
  const [cipler, setCipler] = useState<Cip[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeCitation, setActiveCitation] = useState<string | null>(null)
  const [stage, setStage] = useState<string | null>(null)
  /** The answer as it streams in; empty when nothing is being written. */
  const [writing, setWriting] = useState('')
  const [akisAlistirmalar, setAkisAlistirmalar] = useState<Alistirma[]>([])
  const [odevKey, setOdevKey] = useState('')
  const isWriting = writing !== ''
  const ses = useSes(user?.email, draft, setDraft, () => textareaRef.current?.focus(), saltOkunur)
  const { data: hwData } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  const odevSecenekleri = useMemo(() => {
    const kapali = new Set(['yaptı', 'yapti', 'yapmadı', 'yapmadi', 'eksik'])
    return (hwData.homework || []).filter(hw => {
      if (!hw.homework_key) return false
      return !kapali.has((hw['Ödev Durumu'] || '').toLocaleLowerCase('tr-TR'))
    }).slice(0, 20)
  }, [hwData])

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
  function appendAssistantMessage(payload: AssistantResponse, oneri: Oneri | null = null,
    etkinlikler: { alistirma?: Alistirma[]; netlestirme?: Netlestirme | null; odevOnerisi?: OdevOnerisi | null } = {}) {
    const answer = (payload.answer || '').trim() || 'Yanıt üretilemedi.'
    const assistantMsg: ChatMessage = {
      id: `assistant-${crypto.randomUUID()}`,
      role: 'assistant',
      content: answer,
      citations: payload.citations || [],
      safetyFlags: payload.safety_flags || [],
      planBlocks: payload.plan_blocks || [],
      degraded: payload.meta?.degraded || [],
      model: payload.meta?.model,
      // The stream's own event arrives first; /chat carries the same in the payload.
      modOnerisi: payload.mode_suggestion ?? oneri,
      alistirma: etkinlikler.alistirma ?? (payload.quiz ? [payload.quiz] : []),
      netlestirme: payload.netlestirme ?? etkinlikler.netlestirme,
      odevOnerisi: payload.odev_onerisi ?? etkinlikler.odevOnerisi,
    }
    pendingRequest.current = null
    setMessages(prev => [...prev, assistantMsg])
    void sohbet.yenile()
  }

  async function sohbetAc(id: string, salt: boolean) {
    const result = await sohbet.ac(id, salt)
    if (!result) return
    pendingRequest.current = null
    ogretmen.sec(result.sohbet.ogretmen)
    setMessages(result.mesajlar.length ? result.mesajlar.map(m => ({
      id: m.id, role: m.rol, content: m.icerik,
      citations: kayitliAtiflar(m), ekler: (JSON.parse(m.ekler_json || '[]') as (string | Yukleme)[])
        .map(e => typeof e === 'string' ? e : e.id),
      yuklemeler: m.yuklemeler ?? (JSON.parse(m.ekler_json || '[]') as (string | Yukleme)[])
        .map((e, i) => typeof e === 'string' ? { id: e, ad: `Ek ${i + 1}`, tur: 'bilinmiyor' } : e),
      alistirma: m.alistirma, netlestirme: m.netlestirme, odevOnerisi: m.odev_onerisi,
    })) : [{ id: 'welcome', role: 'assistant', content: '' }])
    setDraft('')
    setCipler([])
    setError(null)
    setActiveCitation(null)
  }

  async function yeniSohbet() {
    try {
      await sohbet.yeni(ogretmen.id)
      pendingRequest.current = null
      setMessages([{ id: 'welcome', role: 'assistant', content: '' }])
      setDraft('')
      setCipler([])
      setError(null)
    } catch { sohbet.setHata('Sohbet kaydedilemedi.') }
  }

  async function sohbetSil(id: string) {
    const acik = sohbet.secili?.id === id
    try {
      await sohbet.sil(id)
      if (acik) {
        pendingRequest.current = null
        setMessages([{ id: 'welcome', role: 'assistant', content: '' }])
        setDraft('')
        setCipler([])
      }
    } catch { sohbet.setHata('Sohbet kaydedilemedi.') }
  }

  async function ogretmenSec(id: string) {
    if (saltOkunur || loading) return
    try {
      if (sohbet.secili) await sohbet.degistir(sohbet.secili.id, { ogretmen: id })
      ogretmen.sec(id)
    } catch { sohbet.setHata('Sohbet kaydedilemedi.') }
  }

  async function yukleBir(yerel: string, file: File) {
    const body = new FormData()
    body.append('dosya', file)
    try {
      const res = await fetch('/api/assistant/uploads', {
        method: 'POST',
        credentials: 'include',
        body,
      })
      let payload: { error?: unknown; id?: unknown; ad?: unknown; tur?: unknown } = {}
      try {
        payload = await res.json()
      } catch {
        payload = {}
      }
      if (!res.ok || typeof payload.id !== 'string') {
        const hata = typeof payload.error === 'string' ? payload.error : 'Dosya yüklenemedi.'
        setCipler(prev => prev.map(c => c.yerel === yerel
          ? { ...c, yukleniyor: false, hata }
          : c))
        return
      }
      setCipler(prev => prev.map(c => c.yerel === yerel ? {
        ...c,
        yukleniyor: false,
        id: payload.id as string,
        ad: typeof payload.ad === 'string' ? payload.ad : c.ad,
        tur: typeof payload.tur === 'string' ? payload.tur : undefined,
      } : c))
    } catch {
      setCipler(prev => prev.map(c => c.yerel === yerel
        ? { ...c, yukleniyor: false, hata: 'Dosya yüklenemedi.' }
        : c))
    }
  }

  function ekle(files: File[]) {
    if (files.length === 0 || saltOkunur || loading) return
    const dolu = cipler.filter(c => c.yukleniyor || c.id).length
    let yer = 4 - dolu
    const baslangic: Cip[] = []
    const yuklenecek: { yerel: string; file: File }[] = []
    for (const file of files) {
      const yerel = crypto.randomUUID()
      if (yer > 0) {
        yer -= 1
        baslangic.push({ yerel, ad: file.name, yukleniyor: true })
        yuklenecek.push({ yerel, file })
      } else {
        baslangic.push({
          yerel,
          ad: file.name,
          hata: 'Bir mesaja en fazla 4 dosya eklenebilir.',
        })
      }
    }
    setCipler(prev => [...prev, ...baslangic])
    for (const item of yuklenecek) void yukleBir(item.yerel, item.file)
  }

  async function odeveBagla(cip: Cip) {
    if (!cip.id || !odevKey || cip.baglaniyor || cip.baglandi) return
    setCipler(prev => prev.map(c => c.yerel === cip.yerel ? { ...c, baglaniyor: true, hata: undefined } : c))
    try {
      const res = await fetch(`/api/assistant/uploads/${cip.id}/odeve-bagla`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anahtar: odevKey }),
      })
      const payload = await res.json()
      if (!res.ok) throw new Error(payload.error || 'Belge ödeve bağlanamadı.')
      setCipler(prev => prev.map(c => c.yerel === cip.yerel ? { ...c, baglaniyor: false, baglandi: true } : c))
      window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
    } catch (e) {
      setCipler(prev => prev.map(c => c.yerel === cip.yerel ? { ...c, baglaniyor: false,
        hata: e instanceof Error ? e.message : 'Belge ödeve bağlanamadı.' } : c))
    }
  }

  const ekleRef = useRef(ekle)
  ekleRef.current = ekle
  // Carbon's TextArea always renders an empty role=alert counter. A chip
  // error is the alert the reader (and the upload checks) should find.
  useLayoutEffect(() => {
    const root = composerRef.current
    if (!root) return
    root.querySelectorAll<HTMLElement>('[class*="text-area__counter-alert"]').forEach(el => {
      if ((el.textContent || '').trim()) return
      el.removeAttribute('role')
      el.removeAttribute('aria-live')
    })
  })
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    // Carbon's TextArea registers its own onPaste and does not call ours.
    const onPaste = (e: ClipboardEvent) => {
      const files = e.clipboardData?.files
      if (files && files.length) {
        e.preventDefault()
        ekleRef.current([...files])
      }
    }
    el.addEventListener('paste', onPaste)
    return () => el.removeEventListener('paste', onPaste)
  }, [])

  async function submit(mode: 'chat' | 'plan', forcedPrompt?: string, opts?: { deep?: boolean; transient?: boolean; retry?: boolean }) {
    const retry = opts?.retry ? pendingRequest.current : null
    const content = (forcedPrompt ?? draft).trim()
    if ((!retry && !content) || loading || saltOkunur || cipler.some(c => c.yukleniyor || c.baglaniyor)) return
    setLoading(true)
    let requestBody: Record<string, unknown>
    if (retry) {
      mode = retry.mode
      requestBody = retry.body
    } else {

      // Normal sends persist only the new turn; the server supplies trusted history.
      // Regeneration and study plans remain independent requests by contract.
      const kaydet = mode === 'chat' && !opts?.deep && !opts?.transient
      let sohbetId = kaydet ? sohbet.secili?.id : undefined
      if (kaydet && !sohbetId) {
        try { sohbetId = await sohbet.yeni(ogretmen.id) }
        catch { setError('Sohbet kaydedilemedi.'); setLoading(false); return }
      }

      const gonderEk = forcedPrompt === undefined && mode === 'chat'
      const ekler = gonderEk ? cipler.flatMap(c => c.id ? [c.id] : []) : []
      const userMsg: ChatMessage = {
        id: `user-${crypto.randomUUID()}`,
        role: 'user',
        content,
        ...(ekler.length ? { ekler, yuklemeler: cipler.flatMap(c => c.id ? [{ id: c.id, ad: c.ad, tur: c.tur || 'bilinmiyor' }] : []) } : {}),
      }

      const nextMessages = [...messages, userMsg]
      const apiKaynak = gonderEk
        ? nextMessages
        : nextMessages.map(m => (m.ekler ? { ...m, ekler: undefined } : m))
      setMessages(nextMessages)
      setDraft('')
      if (gonderEk && ekler.length) setCipler([])

      requestBody = {
        session_id: 'dashboard-default',
        context_filters: {},
        messages: toApiMessages(sohbetId ? [userMsg] : apiKaynak),
        ogretmen: ogretmen.id,
        ...(sohbetId ? { sohbet_id: sohbetId, request_id: crypto.randomUUID() } : {}),
        ...(odevKey ? { odev_anahtari: odevKey } : {}),
        ...(opts?.deep ? { force_deep: true } : {}),
      }

      pendingRequest.current = { mode, body: requestBody }
    }
    setError(null)
    setStage(null)
    setWriting('')
    setAkisAlistirmalar([])

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

    let answered = false
    try {
      const res = await fetch('/api/assistant/stream', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      if (!res.ok || !res.body) throw new Error(`akış açılamadı (${res.status})`)

      let oneri: Oneri | null = null
      let netlestirme: Netlestirme | null = null
      const alistirma: Alistirma[] = []
      let odevOnerisi: OdevOnerisi | null = null
      await readEventStream(res, (name, data) => {
        if (name === 'mode_suggestion') {
          oneri = data as unknown as Oneri
        } else if (name === 'clarify') {
          netlestirme = data as unknown as Netlestirme
        } else if (name === 'quiz') {
          alistirma.push(data as unknown as Alistirma)
          setAkisAlistirmalar([...alistirma])
        } else if (name === 'odev_onerisi') {
          odevOnerisi = data as unknown as OdevOnerisi
        } else if (name === 'tool_start') {
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
          appendAssistantMessage(data.payload as AssistantResponse, oneri, { alistirma: alistirma.length ? alistirma : undefined, netlestirme, odevOnerisi })
          setAkisAlistirmalar([])
        } else if (name === 'error') {
          throw new Error(String(data.error ?? 'akış hatası'))
        }
      })
      if (!answered) throw new Error('akış yanıtsız kapandı')
    } catch (streamErr) {
      if (answered) return
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
      setAkisAlistirmalar([])
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
    void submit('chat', prompt, { transient: true })
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
    // data-ogretmen names the mode; the family class brings that subject's role tokens
    // (theme/_subjects.scss), which AssistantChat.scss applies only when the mode is not
    // Genel. The brand band is outside this section and never changes.
    <section
      className={['ac', secili && subjectClass(null, secili.renk_ailesi)].filter(Boolean).join(' ')}
      data-ogretmen={ogretmen.id}
    >
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
            <p className="ac__subtitle">
              {secili ? `${secili.ogretmen_adi} — konuyu adım adım anlatır` : 'Kaynaklı soru-cevap ve kişisel çalışma planı'}
            </p>
          </div>
        </div>
      </header>

      <OgretmenSecici
        liste={ogretmen.liste}
        secili={ogretmen.id}
        onSec={id => void ogretmenSec(id)}
        hata={ogretmen.hata ? voice.ogretmenHata : null}
      />

      {/* Quick prompts */}
      <div className="ac__prompts">
        {prompts.map(qp => (
          <button
            key={qp.text}
            type="button"
            className={qp.primary ? 'ac__prompt-chip ac__prompt-chip--primary' : 'ac__prompt-chip'}
            onClick={() => void submit(qp.mode, qp.text)}
            disabled={loading || saltOkunur}
          >
            <qp.icon size={16} />
            {qp.text}
          </button>
        ))}
      </div>

      <div className="ac__layout">
        <SohbetListesi depo={sohbet} student={isStudent} disabled={loading || sohbet.bekliyor}
          onAc={(id, salt) => void sohbetAc(id, salt)} onYeni={() => void yeniSohbet()}
          onSil={id => void sohbetSil(id)} />
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
                  <div className={msg.role === 'assistant' ? 'ac-msg__content ac-md' : 'ac-msg__content ac-msg__content--own'}>
                    {msg.role === 'assistant'
                      ? <AnswerBody text={msg.id === 'welcome' ? welcome : msg.content}
                          citations={msg.citations ?? []} onActivate={activateCitation} />
                      : msg.content}
                  </div>
                  {msg.yuklemeler?.map(ek => <YuklenenEk key={ek.id} ek={ek} odevler={odevSecenekleri}
                    saltOkunur={saltOkunur} disabled={loading} />)}
                  {msg.alistirma?.map(a => <AlistirmaKarti key={a.id} alistirma={a}
                    saltOkunur={saltOkunur} disabled={loading}
                    onYanlislar={metin => void submit('chat', `Yanlış yaptığım bu soruları açıklar mısın?\n${metin}`)} />)}
                  {msg.odevOnerisi && <OdevOnayKarti oneri={msg.odevOnerisi} saltOkunur={saltOkunur || loading} />}
                  {msg.netlestirme && <NetlestirmeSecenekleri secenekler={msg.netlestirme.secenekler}
                    etkin={msg.id === latestAssistant?.id && !loading && !saltOkunur}
                    onSec={metin => void submit('chat', metin)} onBaska={() => textareaRef.current?.focus()} />}
                  {msg.safetyFlags && msg.safetyFlags.length > 0 && (
                    <div className="ac-msg__flags">
                      {msg.safetyFlags.map(f => (
                        <Tag key={f} type={flagTone(f)} size="sm">{FLAG_LABELS[f] ?? f}</Tag>
                      ))}
                    </div>
                  )}
                  {/* Only while still in Genel, and only for a teacher the list has: once the
                      reader has moved, or the teacher is gone, the button would do nothing. */}
                  {msg.modOnerisi && ogretmen.id === GENEL
                    && ogretmen.liste.some(o => o.id === msg.modOnerisi?.ogretmen) && (
                    <ModOnerisi oneri={msg.modOnerisi}
                      onGec={async () => {
                        const id = msg.modOnerisi!.ogretmen
                        await ogretmenSec(id)
                        // The button unmounts with the switch. Left alone, focus
                        // falls to the document and the new teacher is never
                        // announced. The radio is already on the page; focusing
                        // it names the choice, and the chip's :focus-visible
                        // ring draws for this keyboard action.
                        document.querySelector<HTMLInputElement>(
                          `input[name="ac-ogretmen"][value="${CSS.escape(id)}"]`,
                        )?.focus({ focusVisible: true } as FocusOptions)
                      }} />
                  )}
                  {msg.role === 'assistant' && msg.id !== 'welcome' && (
                    <div className="ac-msg__actions">
                      <IconButton kind="ghost" size="sm" label="Kopyala"
                        onClick={() => void navigator.clipboard.writeText(msg.content)}>
                        <Copy />
                      </IconButton>
                      <IconButton kind="ghost" size="sm" label="Yeniden üret"
                        disabled={loading || saltOkunur}
                        onClick={() => void regenerate(msg.id)}>
                        <Renew />
                      </IconButton>
                      <Button kind="ghost" size="sm" renderIcon={Search}
                        disabled={loading || saltOkunur}
                        onClick={() => deepen(msg.id)}>
                        Daha derine in
                      </Button>
                      {ses.ses && okunacakMetin(msg.content) && <Button kind="ghost" size="sm"
                        aria-pressed={ses.okunan === msg.id} onClick={() => ses.oku(msg.id, msg.content)}>
                        {ses.okunan === msg.id ? 'Durdur' : 'Sesli oku'}
                      </Button>}
                    </div>
                  )}
                </div>
              </article>
            ))}

            {akisAlistirmalar.map(a => <AlistirmaKarti key={a.id} alistirma={a}
              disabled saltOkunur={saltOkunur} onYanlislar={() => {}} />)}
            {loading && (isWriting
              ? <WritingAnswer text={writing} />
              : <ThinkingIndicator stage={stage} />)}
            <div ref={messagesEndRef} />
          </div>

          {/* Composer */}
          {isStudent && <p className="ac__aile-notu">Sohbetlerini ailen de görebilir.</p>}
          {saltOkunur && <p className="ac__aile-notu">Bu sohbet salt okunur.</p>}
          <form
            ref={composerRef}
            className="ac__composer"
            onSubmit={onSubmit}
            onDragOver={e => { e.preventDefault() }}
            onDrop={e => {
              e.preventDefault()
              ekle([...(e.dataTransfer.files ?? [])])
            }}
          >
            {cipler.length > 0 && (
              <ul className="ac__ekler">
                {cipler.map(c => (
                  <li key={c.yerel} className="ac__ek">
                    {c.id && c.tur === 'gorsel' && <img className="ac__ek-onizleme"
                      src={`/api/assistant/uploads/${c.id}`} alt="Yüklenen görsel" />}
                    <span>{c.ad}</span>
                    {c.tur && TUR[c.tur] ? <span>{TUR[c.tur]}</span> : null}
                    {c.yukleniyor ? <span>Yükleniyor</span> : null}
                    {c.id && c.tur !== 'gorsel' && <Button kind="ghost" size="sm"
                      disabled={loading || saltOkunur || !odevKey || c.baglaniyor || c.baglandi}
                      onClick={() => void odeveBagla(c)}>
                      {c.baglandi ? 'Ödeve bağlandı' : c.baglaniyor ? 'Bağlanıyor…' : 'Bu ödeve bağla'}
                    </Button>}
                    {c.hata ? <p role="alert" className="ac__ek-hata">{c.hata}</p> : null}
                    <button
                      type="button"
                      className="ac__ek-kaldir"
                      aria-label={`Kaldır: ${c.ad}`}
                      disabled={loading || saltOkunur}
                      onClick={() => setCipler(prev => prev.filter(x => x.yerel !== c.yerel))}
                    >
                      <Close size={16} aria-hidden />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <Select
              id="ac-odev"
              className="ac__odev"
              labelText="Ödev"
              value={odevKey}
              onChange={e => setOdevKey(e.target.value)}
              disabled={loading || saltOkunur}
            >
              <SelectItem value="" text="Seçilmedi — genel soru" />
              {odevSecenekleri.map(hw => {
                const ad = `${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}`
                return (
                  <SelectItem
                    key={hw.homework_key}
                    value={hw.homework_key || ''}
                    text={ad.length > 80 ? `${ad.slice(0, 79)}…` : ad}
                  />
                )
              })}
            </Select>
            <div className="ac__input-row">
              <YuklemeAlani onDosyalar={ekle} disabled={loading || saltOkunur} />
              <TextArea
                ref={textareaRef}
                id="ac-input"
                labelText="Sorun"
                hideLabel
                value={draft}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={e => {
                  const files = e.clipboardData?.files
                  if (files && files.length) {
                    e.preventDefault()
                    ekle([...files])
                  }
                }}
                rows={2}
                placeholder={loading ? 'Yanıt bekleniyor...' : voice.placeholder}
                disabled={loading || saltOkunur}
                className="ac__textarea"
              />
              <div className="ac__send-group">
                {ses.mikrofonVar && <IconButton kind="ghost" size="lg"
                  label={ses.dinliyor ? 'Dinlemeyi bitir' : 'Sesle sor'} disabled={loading}
                  onClick={ses.mikrofon}><Microphone /></IconButton>}
                <IconButton
                  kind="primary"
                  label="Gönder"
                  size="lg"
                  disabled={loading || saltOkunur || !draft.trim() || cipler.some(c => c.yukleniyor)}
                  type="submit"
                >
                  <Send />
                </IconButton>
                <IconButton
                  kind="ghost"
                  label="Çalışma Planı"
                  size="lg"
                  disabled={loading || saltOkunur || !draft.trim() || cipler.some(c => c.yukleniyor)}
                  onClick={() => void submit('plan')}
                >
                  <CalendarHeatMap />
                </IconButton>
              </div>
            </div>
            {ses.hata && <p role="alert" className="ac__ses-hata">{ses.hata}</p>}
            {error && (
              <div className="ac__error">
                <Tag type="red" size="sm">{error}</Tag>
                <Button
                  kind="ghost"
                  size="sm"
                  renderIcon={Renew}
                  onClick={() => {
                    setError(null)
                    void submit('chat', undefined, { retry: true })
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
      <Modal open={ses.onayAcik} modalHeading="Mikrofon" primaryButtonText="Onayla" secondaryButtonText="Vazgeç"
        onRequestSubmit={ses.onayla} onRequestClose={ses.vazgec} onSecondarySubmit={ses.vazgec}>
        <p>Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.</p>
      </Modal>
    </section>
  )
}
