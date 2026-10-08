import { useCallback, useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import type { ChatContainerProps, ChatInstance, CustomSendMessageOptions, MessageRequest, StreamChunk } from '@carbon/ai-chat'
import { useSession } from '../contexts/session'
import { GENEL, useOgretmen } from '../hooks/useOgretmen'
import { useSohbetler } from '../hooks/useSohbetler'
import { useSes } from '../hooks/useSes'
import { asistanDeposu } from './asistanDeposu.ts'
import { akisBaslat, hataYaniti, olayIsle, sonYanit } from './olayEslemesi.ts'
import type { SonYanitSecenekleri } from './olayEslemesi.ts'
import { okurHatasi, planGonder, soruGonder } from './akisIstemcisi.ts'
import { tedyChatConfig } from './tedyChatConfig.ts'
import { TEDY_MARKDOWN_EKLENTILERI } from './markdownKurulumu.ts'
import { tabloCiz } from './Tablo.tsx'
import { VOICE } from './ses.ts'

function secenekler(): SonYanitSecenekleri {
  const d = asistanDeposu.al()
  return { geriBildirim: !d.saltOkunur, ogrenci: d.okur === 'ogrenci' }
}

/** Bir isteği çalıştırır ve Carbon'a parça parça verir. Parçalar sırayla eklenir (addMessageChunk asenkron). */
async function calistir(inst: ChatInstance, govde: Record<string, unknown>, plan: boolean, signal: AbortSignal) {
  asistanDeposu.ayarla({ bekleyen: { govde, plan }, yukleniyor: true })
  let d = akisBaslat(crypto.randomUUID())
  let zincir: Promise<unknown> = Promise.resolve()
  const sira = (f: () => Promise<unknown>) => { zincir = zincir.then(f); return zincir }
  try {
    if (plan) {
      const p = await planGonder(govde, signal)
      await inst.messaging.addMessageChunk({ final_response: sonYanit(d, p, secenekler()) } as StreamChunk)
      asistanDeposu.ayarla({ sonYanitId: d.yanitId, sonModel: p.meta?.model })
    } else {
      await soruGonder(govde, o => {
        const r = olayIsle(d, o, secenekler())
        d = r.durum
        if (r.kaldir) { const k = r.kaldir; sira(() => inst.messaging.removeMessages(k)) }
        for (const p of r.parcalar) sira(() => inst.messaging.addMessageChunk(p))
        if (o.ad === 'answer') {
          const payload = o.veri.payload as { answer?: string; meta?: { model?: string } }
          const dk = asistanDeposu.al()
          asistanDeposu.ayarla({ dokum: [...dk.dokum, { role: 'assistant', content: payload.answer ?? '' }],
            sonYanitId: d.yanitId, sonModel: payload.meta?.model })
        }
      }, signal)
      await zincir
    }
    asistanDeposu.ayarla({ bekleyen: null })
  } catch (e) {
    await zincir.catch(() => {})
    if ((e as { name?: string })?.name === 'AbortError' || signal.aborted) return
    await inst.messaging.addMessage(hataYaniti(crypto.randomUUID(), okurHatasi(e)))
  } finally {
    asistanDeposu.ayarla({ yukleniyor: false })
  }
}

export async function tekrarDene(inst: ChatInstance, hataMesajiId: string) {
  const b = asistanDeposu.al().bekleyen
  if (!b) return
  await inst.messaging.removeMessages([hataMesajiId])
  await calistir(inst, b.govde, b.plan, new AbortController().signal)
}

export async function soruyuYeniden(inst: ChatInstance, metin: string, ek: { deep?: boolean; transient?: boolean; plan?: boolean }) {
  asistanDeposu.ayarla({ sonrakiIstek: ek })
  await inst.send(metin)
}

const TABLO = { table: tabloCiz }

/** Gönderme işlevi Carbon'un yapılandırmasında yaşar; güncel sohbet deposunu render dışında buradan okur. */
let guncelSohbet: ReturnType<typeof useSohbetler> | null = null

export function useAsistanSohbeti(bicim: 'sayfa' | 'panel') {
  const user = useSession()
  const ogrenci = user?.student === true
  const okur = ogrenci ? 'ogrenci' : 'aile'
  const ogretmen = useOgretmen(user?.email)
  const sohbet = useSohbetler(user?.email, ogrenci)
  const instance = useRef<ChatInstance | null>(null)
  const salt = sohbet.secili?.salt === true

  const secili = ogretmen.secili
  const karsilama = secili ? secili.karsilama[okur] : VOICE[okur].welcome
  const hizliSorular = useMemo<{ metin: string; plan?: boolean }[]>(() => secili
    ? secili.hizli_sorular[okur].map(metin => ({ metin }))
    : VOICE[okur].prompts.map(p => ({ metin: p.text, plan: p.mode === 'plan' })), [secili, okur])

  // Render sırasında değil: depo dinleyicileri başka bileşenlerdir.
  useLayoutEffect(() => { guncelSohbet = sohbet }, [sohbet])
  useLayoutEffect(() => {
    asistanDeposu.ayarla({ okur, email: user?.email, ogretmenId: ogretmen.id ?? GENEL,
      saltOkunur: salt, sohbetId: sohbet.secili?.id })
  }, [okur, user?.email, ogretmen.id, salt, sohbet.secili?.id])

  // Taslak Carbon'un giriş alanındadır; ses kancası onu ihtiyaç anında okur ve yazar.
  const ses = useSes(user?.email, () => instance.current?.getState().input.rawValue ?? '',
    metin => instance.current?.input.updateRawValue(() => metin), () => { instance.current?.requestFocus() }, salt)
  useEffect(() => {
    asistanDeposu.ayarla({ ses: { var: !!ses.ses, okunan: ses.okunan, oku: ses.oku } })
  }, [ses.ses, ses.okunan, ses.oku])

  const gonder = useCallback(async (istek: MessageRequest, sec: CustomSendMessageOptions, inst: ChatInstance) => {
    const metin = String((istek.input as { text?: string }).text ?? '').trim()
    const d = asistanDeposu.al()
    if (!metin || d.saltOkunur) return
    const ek = d.sonrakiIstek
    const plan = !!ek.plan || hizliSorular.some(s => s.plan && s.metin === metin)
    const kaydet = !plan && !ek.deep && !ek.transient
    let sohbetId = kaydet ? d.sohbetId : undefined
    if (kaydet && !sohbetId) {
      try { sohbetId = await guncelSohbet!.yeni(d.ogretmenId) } catch {
        await inst.messaging.addMessage(hataYaniti(crypto.randomUUID(), 'Sohbet kaydedilemedi.')); return
      }
    }
    const ekler = !ek.deep && !ek.transient && !plan ? d.cipler.flatMap(c => c.id ? [c.id] : []) : []
    const kullanici = { role: 'user' as const, content: metin, ...(ekler.length ? { ekler } : {}) }
    const dokum = [...d.dokum, { role: 'user' as const, content: metin }]
    const govde: Record<string, unknown> = {
      session_id: 'dashboard-default', context_filters: {},
      messages: sohbetId ? [kullanici] : dokum, ogretmen: d.ogretmenId,
      ...(sohbetId ? { sohbet_id: sohbetId, request_id: crypto.randomUUID() } : {}),
      ...(d.odevKey ? { odev_anahtari: d.odevKey } : {}),
      ...(ek.deep ? { force_deep: true } : {}),
      ...(d.sayfa ? { sayfa: { ad: d.sayfa.ad, ...(d.sayfa.oge ? { oge: d.sayfa.oge } : {}) } } : {}),
    }
    const goruntu = d.cipler.flatMap(c => c.id ? [{ id: c.id, ad: c.ad, tur: c.tur ?? 'bilinmiyor' }] : [])
    asistanDeposu.ayarla({ sonrakiIstek: {}, dokum, sayfa: null,
      ...(ekler.length ? { cipler: [], ekGoruntuleri: { ...d.ekGoruntuleri, [istek.id ?? '']: goruntu } } : {}) })
    await calistir(inst, govde, plan, sec.signal)
    void guncelSohbet?.yenile()
  }, [hizliSorular])

  const config = useMemo(() => tedyChatConfig({
    bicim, okur, karsilama, hizliSorular, saltOkunur: salt,
    altBaslik: secili ? `${secili.ogretmen_adi} — konuyu adım adım anlatır` : 'Kaynaklı soru-cevap ve kişisel çalışma planı',
    gonder,
  }), [bicim, okur, karsilama, hizliSorular, salt, secili, gonder])

  const props: ChatContainerProps = {
    ...config,
    markdown: { markdownItPlugins: TEDY_MARKDOWN_EKLENTILERI, customRenderers: TABLO },
    onBeforeRender: inst => { instance.current = inst },
  }
  return { props, instance, ogretmen, sohbet, bicim, ses }
}
