import { useCallback, useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import type { ChatContainerProps, ChatInstance, CustomSendMessageOptions, MessageRequest } from '@carbon/ai-chat'
import { useSession } from '../contexts/session'
import { GENEL, useOgretmen } from '../hooks/useOgretmen'
import { useSohbetler } from '../hooks/useSohbetler'
import { useSes } from '../hooks/useSes'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { hataYaniti } from './olayEslemesi.ts'
import { calistir } from './istek.ts'
import { tedyChatConfig } from './tedyChatConfig.ts'
import { TEDY_MARKDOWN_EKLENTILERI } from './markdownKurulumu.ts'
import { tabloCiz } from './Tablo.tsx'
import { VOICE } from './ses.ts'
import { ozelYanitCizici } from './ozelYanit.tsx'
import KaynakPaneli from './KaynakPaneli.tsx'
import AiAciklama from './AiAciklama.tsx'
import { altbilgiCizici } from './altbilgi.tsx'
import { geriBildirimGonder } from './geriBildirim.ts'
import GecmisPaneli from './GecmisPaneli.tsx'
import IstekEkleri from './IstekEkleri.tsx'
import { etkinSohbetiOku, etkinSohbetiYaz, yeniSohbet } from './useAsistanOturumu.ts'
import { gecmisOgeleri } from './gecmis.ts'
import type { BusEventFeedback } from '@carbon/ai-chat'

const TABLO = { table: tabloCiz }
const ALTBILGI = altbilgiCizici()

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
      try {
        sohbetId = await guncelSohbet!.yeni(d.ogretmenId)
        etkinSohbetiYaz(d.email, { id: sohbetId, salt: false })
      } catch {
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
    asistanDeposu.ayarla({ sonrakiIstek: {}, dokum, sayfa: null, mesajVar: true,
      ...(ekler.length ? { cipler: [], ekGoruntuleri: { ...d.ekGoruntuleri, [istek.id ?? '']: goruntu } } : {}) })
    await calistir(inst, govde, plan, sec.signal)
    void guncelSohbet?.yenile()
  }, [hizliSorular])

  const ogretmenSec = useCallback(async (id: string) => {
    const d = asistanDeposu.al()
    if (d.saltOkunur || d.yukleniyor) return
    if (d.sohbetId) await guncelSohbet?.degistir(d.sohbetId, { ogretmen: id })
    ogretmen.sec(id)
    // Düğme geçişle kaybolur; odak seçilen öğretmene gider ve seçim duyurulur.
    document.querySelector<HTMLInputElement>(`input[name="ac-ogretmen"][value="${CSS.escape(id)}"]`)
      ?.focus({ focusVisible: true } as FocusOptions)
  }, [ogretmen])
  const ozelYanit = useMemo(() => ozelYanitCizici(ogretmenSec), [ogretmenSec])

  const email = user?.email
  const mesajVar = useAsistanDurumu(d => d.mesajVar)
  const gecmisYukle = useCallback(async () => {
    const etkin = etkinSohbetiOku(email)
    if (!etkin || !guncelSohbet) return []
    const sonuc = await guncelSohbet.ac(etkin.id, etkin.salt)
    if (!sonuc) { etkinSohbetiYaz(email, null); return [] }
    const saltMi = sonuc.read_only ?? etkin.salt
    const ekGoruntuleri: Record<string, { id: string; ad: string; tur: string }[]> = {}
    for (const m of sonuc.mesajlar) if (m.rol === 'user' && m.yuklemeler?.length) ekGoruntuleri[m.id] = m.yuklemeler
    asistanDeposu.ayarla({ sohbetId: etkin.id, saltOkunur: saltMi, ekGoruntuleri, mesajVar: sonuc.mesajlar.length > 0,
      dokum: sonuc.mesajlar.map(m => ({ role: m.rol, content: m.icerik })) })
    return gecmisOgeleri(sonuc.mesajlar, { geriBildirim: !saltMi, ogrenci: okur === 'ogrenci' })
  }, [email, okur])

  const config = useMemo(() => tedyChatConfig({
    bicim, okur, karsilama, hizliSorular, saltOkunur: salt,
    altBaslik: secili ? `${secili.ogretmen_adi} — konuyu adım adım anlatır` : 'Kaynaklı soru-cevap ve kişisel çalışma planı',
    gonder, gecmisYukle, mesajVar,
  }), [bicim, okur, karsilama, hizliSorular, salt, secili, gonder, gecmisYukle, mesajVar])

  const props: ChatContainerProps = {
    ...config,
    markdown: { markdownItPlugins: TEDY_MARKDOWN_EKLENTILERI, customRenderers: TABLO },
    onBeforeRender: inst => {
      instance.current = inst
      inst.on([
        { type: 'feedback' as never, handler: (e: unknown) => void geriBildirimGonder(e as BusEventFeedback) },
        // Carbon'un "Yeni sohbet" ve yeniden başlat düğmeleri de yeni kayıt açar.
        { type: 'history:newChat' as never, handler: () => { if (guncelSohbet) void yeniSohbet(inst, guncelSohbet) } },
        { type: 'restartConversation' as never, handler: () => { if (guncelSohbet) void yeniSohbet(inst, guncelSohbet) } },
      ])
      if (asistanDeposu.al().saltOkunur) inst.updateInputIsDisabled(true)
    },
    renderUserDefinedResponse: ozelYanit,
    renderCustomMessageFooter: ALTBILGI,
    renderCustomRequestFooter: (_slot, mesaj) => <IstekEkleri mesajId={mesaj.id} />,
    renderWriteableElements: {
      workspacePanelElement: <KaynakPaneli />, headerFixedActionsElement: <AiAciklama />,
      historyPanelElement: <GecmisPaneli depo={sohbet} ogrenci={ogrenci} inst={() => instance.current} ogretmenSec={ogretmen.sec} />,
    },
  }
  return { props, instance, ogretmen, ogretmenSec, sohbet, bicim, ses }
}
