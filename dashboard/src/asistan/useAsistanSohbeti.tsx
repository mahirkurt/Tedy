import { useCallback, useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import type { ChatContainerProps, ChatInstance, CustomSendMessageOptions, MessageRequest } from '@carbon/ai-chat'
import { useSession } from '../contexts/session'
import { GENEL, useOgretmen } from '../hooks/useOgretmen'
import { useSohbetler } from '../hooks/useSohbetler'
import { useSes } from '../hooks/useSes'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { hataYaniti } from './olayEslemesi.ts'
import { IstekHatasi, okurHatasi } from './akisIstemcisi.ts'
import { calistir, metinGondericiKur, tekrariDurdur } from './istek.ts'
import { tedyChatConfig } from './tedyChatConfig.ts'
import { TEDY_MARKDOWN_EKLENTILERI, useKatexHazir } from './markdownKurulumu.ts'
import { tabloCiz } from './Tablo.tsx'
import { VOICE } from './ses.ts'
import { ozelYanitCizici } from './ozelYanit.tsx'
import KaynakPaneli from './KaynakPaneli.tsx'
import AiAciklama from './AiAciklama.tsx'
import { altbilgiCizici } from './altbilgi.tsx'
import { geriBildirimGonder } from './geriBildirim.ts'
import GecmisPaneli from './GecmisPaneli.tsx'
import IstekEkleri from './IstekEkleri.tsx'
import GirisEkleri from './GirisEkleri.tsx'
import Karsilama from './Karsilama.tsx'
import GirisDugmeleri, { GirisEylemleri } from './GirisDugmeleri.tsx'
import OgretmenSecimi, { OGRETMEN_SECIMI_ID } from './OgretmenSecimi.tsx'
import { etkinSohbetiOku, etkinSohbetiYaz, gecmisiAc, yeniSohbet } from './useAsistanOturumu.ts'
import { RecentlyViewed } from '@carbon/icons-react'
import { gecmisOgeleri } from './gecmis.ts'
import type { BusEventFeedback } from '@carbon/ai-chat'
import { sabitOgeyiBirak, sayfaEtiketi, useAcikOge } from './sayfaBaglami.ts'
import { sayfaSorulari } from './sayfaSorulari.ts'
import BaglamCipi from './BaglamCipi.tsx'
import GirisUyarisi from './GirisUyarisi.tsx'

const TABLO = { table: tabloCiz }
const ALTBILGI = altbilgiCizici()

const ekBekliyor = () => asistanDeposu.al().cipler.some(c => c.yukleniyor || c.baglaniyor)
function eklerHazir(signal?: AbortSignal): Promise<void> {
  if (!ekBekliyor()) return Promise.resolve()
  return new Promise(bitti => {
    const birak = asistanDeposu.abone(() => { if (!ekBekliyor()) { birak(); bitti() } })
    signal?.addEventListener('abort', () => { birak(); bitti() }, { once: true })
  })
}

/** Gönderme işlevi Carbon'un yapılandırmasında yaşar; güncel sohbet deposunu render dışında buradan okur. */
let guncelSohbet: ReturnType<typeof useSohbetler> | null = null
/** Başlıktaki "Sohbetler" eylemi yapılandırmada yaşar; çizilen sohbetin örneğini render dışında buradan okur. */
let gecmisOrnegi: ChatInstance | null = null
/** Soruyla giden sabit öğe ("Asistana sor", B78) bırakılınca açık öğe değişir; bu tek değişim bağlam çipini geri
 *  getirmemeli (çip ilk sorudan sonra düşer). */
let baglamiAtla = false
function gecmisiDegistir() {
  const i = gecmisOrnegi
  if (i) void gecmisiAc(i, !i.getState().customPanels.history.isOpen)
}

/** `sayfa`: bulunulan sayfanın adı (sayfaBaglami.ts) — başlatıcı paneli ya da /asistan?sayfa=…; yoksa null. */
export function useAsistanSohbeti(bicim: 'sayfa' | 'panel', sayfa: string | null = null) {
  const user = useSession()
  const ogrenci = user?.student === true
  const okur = ogrenci ? 'ogrenci' : 'aile'
  const ogretmen = useOgretmen(user?.email)
  const sohbet = useSohbetler(user?.email, ogrenci)
  const instance = useRef<ChatInstance | null>(null)
  const salt = sohbet.secili?.salt === true

  // Sayfa bağlamı: açılışta ve sayfa ya da açık öğe değişince yazılır; ilk sorudan sonra (gonder) ya da çip
  // kapatılınca null olur. Bağlamsız açılış eski bağlamı da siler (başlatıcıdan kalan çip /asistan'a taşınmaz).
  // İlkel bağımlılıklar: aynı öğe yeniden bildirildiğinde (nesne değişse de) okurun kapattığı çip geri gelmez.
  const oge = useAcikOge()
  const ogeTur = oge?.tur, ogeId = oge?.id, ogeEtiket = oge?.etiket
  const ogeKip = oge?.kilavuz?.kip, ogeSenaryo = oge?.kilavuz?.senaryo
  useLayoutEffect(() => {
    if (baglamiAtla) { baglamiAtla = false; return }
    const etiket = sayfaEtiketi(sayfa)
    asistanDeposu.ayarla({ sayfa: sayfa && etiket ? { ad: sayfa, etiket,
      ...(ogeTur && ogeId ? { oge: { tur: ogeTur, id: ogeId, ...(ogeKip ? { kip: ogeKip, senaryo: ogeSenaryo ?? null } : {}) }, ogeEtiketi: ogeEtiket } : {}) } : null })
  }, [sayfa, ogeTur, ogeId, ogeEtiket, ogeKip, ogeSenaryo])
  const baglam = useAsistanDurumu(d => d.sayfa?.ad ?? null)

  const secili = ogretmen.secili
  const karsilama = secili ? secili.karsilama[okur] : VOICE[okur].welcome
  const hizliSorular = useMemo<{ metin: string; plan?: boolean }[]>(() => baglam
    ? sayfaSorulari(baglam, okur).map(metin => ({ metin }))
    : secili
      ? secili.hizli_sorular[okur].map(metin => ({ metin }))
      : VOICE[okur].prompts.map(p => ({ metin: p.text, plan: p.mode === 'plan' })), [baglam, secili, okur])

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

  // Sorunun gövdesini kurup çalıştırır. Carbon'un gönderimi ve sohbet açılamadan düşen sorunun "Tekrar dene"si
  // (istek.ts metinGonderici) aynı yolu kullanır; soru balonu zaten ekrandadır.
  const metniGonder = useCallback(async (inst: ChatInstance, metin: string, signal: AbortSignal, istekId?: string) => {
    // Yüklenen ya da ödeve bağlanan ek bitene kadar beklenir (eski arayüz gönderimi engelliyordu): yoksa ek
    // bu sorudan düşer, çipi temizlenir ve yükleme sonucu boşa gider.
    await eklerHazir(signal)
    if (signal.aborted) return
    const d = asistanDeposu.al()
    const ek = d.sonrakiIstek
    const plan = !!ek.plan || hizliSorular.some(s => s.plan && s.metin === metin)
    const kaydet = !plan && !ek.deep && !ek.transient
    let sohbetId = kaydet ? d.sohbetId : undefined
    if (kaydet && !sohbetId) {
      try {
        sohbetId = await guncelSohbet!.yeni(d.ogretmenId)
        etkinSohbetiYaz(d.email, { id: sohbetId, salt: false })
      } catch (e) {
        // Oturum düştüyse okura oturum cümlesi; kart aynı soruyu yeniden yollayabilir.
        const oturum = e instanceof IstekHatasi && (e.durum === 401 || e.durum === 403)
        await inst.messaging.addMessage(hataYaniti(crypto.randomUUID(), oturum ? okurHatasi(e) : 'Sohbet kaydedilemedi.', { metin }))
        return
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
    // "Asistana sor" ile sabitlenen öğe bu soruyla gitti (B78); bırakılması bağlam çipini geri getirmez.
    if (sabitOgeyiBirak()) baglamiAtla = true
    asistanDeposu.ayarla({ sonrakiIstek: {}, dokum, sayfa: null, mesajVar: true,
      ...(ekler.length ? { cipler: [], ekGoruntuleri: { ...d.ekGoruntuleri, ...(istekId ? { [istekId]: goruntu } : {}) } } : {}) })
    await calistir(inst, govde, plan, signal)
    void guncelSohbet?.yenile()
  }, [hizliSorular])
  useLayoutEffect(() => { metinGondericiKur(metniGonder) }, [metniGonder])

  const gonder = useCallback(async (istek: MessageRequest, sec: CustomSendMessageOptions, inst: ChatInstance) => {
    const metin = String((istek.input as { text?: string }).text ?? '').trim()
    if (!metin || asistanDeposu.al().saltOkunur) return
    await metniGonder(inst, metin, sec.signal, istek.id)
  }, [metniGonder])

  const ogretmenSec = useCallback(async (id: string) => {
    const d = asistanDeposu.al()
    if (d.saltOkunur || d.yukleniyor) return
    if (d.sohbetId) await guncelSohbet?.degistir(d.sohbetId, { ogretmen: id })
    ogretmen.sec(id)
    // Öneri düğmesi geçişle kaybolur; odak öğretmen seçimine gider (seçilen öğretmen orada okunur).
    document.getElementById(OGRETMEN_SECIMI_ID)?.querySelector<HTMLButtonElement>('button')
      ?.focus({ focusVisible: true } as FocusOptions)
  }, [ogretmen])
  const ozelYanit = useMemo(() => ozelYanitCizici(ogretmenSec), [ogretmenSec])

  const email = user?.email
  const gecmisYukle = useCallback(async () => {
    const etkin = etkinSohbetiOku(email)
    if (!etkin || !guncelSohbet) return []
    const sonuc = await guncelSohbet.ac(etkin.id, etkin.salt)
    if (!sonuc) { etkinSohbetiYaz(email, null); asistanDeposu.ayarla({ sohbetId: undefined }); return [] }
    const saltMi = sonuc.read_only ?? etkin.salt
    const ekGoruntuleri: Record<string, { id: string; ad: string; tur: string }[]> = {}
    for (const m of sonuc.mesajlar) if (m.rol === 'user' && m.yuklemeler?.length) ekGoruntuleri[m.id] = m.yuklemeler
    asistanDeposu.ayarla({ sohbetId: etkin.id, saltOkunur: saltMi, ekGoruntuleri, mesajVar: sonuc.mesajlar.length > 0,
      dokum: sonuc.mesajlar.map(m => ({ role: m.rol, content: m.icerik })) })
    return gecmisOgeleri(sonuc.mesajlar, { geriBildirim: !saltMi, ogrenci: okur === 'ogrenci' })
  }, [email, okur])

  // "Sohbetler": geçmiş paneli kapalı başlar (history.startClosed) ve bu eylemle açılır/kapanır; basılı hâli panelin
  // durumunu izler (state:change).
  const gecmisAcik = useAsistanDurumu(d => d.gecmisAcik)
  const eylemler = useMemo(() => [{ text: 'Sohbetler', icon: RecentlyViewed, fixed: true, isSelected: gecmisAcik,
    onClick: gecmisiDegistir }], [gecmisAcik])
  const config = useMemo(() => tedyChatConfig({
    bicim, okur, saltOkunur: salt, baslik: secili ? secili.ogretmen_adi : 'Genel asistan', eylemler,
    gonder, gecmisYukle,
  }), [bicim, okur, salt, secili, eylemler, gonder, gecmisYukle])

  const props: ChatContainerProps = {
    ...config,
    markdown: { markdownItPlugins: TEDY_MARKDOWN_EKLENTILERI, customRenderers: TABLO },
    onBeforeRender: inst => {
      instance.current = inst
      gecmisOrnegi = inst
      inst.on([
        { type: 'feedback' as never, handler: (e: unknown) => void geriBildirimGonder(e as BusEventFeedback) },
        // Carbon'un "Yeni sohbet" ve yeniden başlat düğmeleri de yeni kayıt açar.
        { type: 'history:newChat' as never, handler: () => { if (guncelSohbet) void yeniSohbet(inst, guncelSohbet) } },
        { type: 'restartConversation' as never, handler: () => { if (guncelSohbet) void yeniSohbet(inst, guncelSohbet) } },
        // Durdur düğmesi "Tekrar dene"nin başlattığı isteği de keser (Carbon'un kendi gönderiminin dışında koşar).
        { type: 'stopStreaming' as never, handler: () => tekrariDurdur() },
        // Giriş alanının boşluğu (yazma, mikrofon, gönderim sonrası temizlenme) Carbon'un durum olayıyla izlenir.
        { type: 'state:change' as never, handler: () => {
          const durum = inst.getState()
          const bos = !durum.input.rawValue.trim()
          const gecmis = !!durum.customPanels?.history?.isOpen
          const d = asistanDeposu.al()
          if (d.girisBos !== bos || d.gecmisAcik !== gecmis) asistanDeposu.ayarla({ girisBos: bos, gecmisAcik: gecmis })
        } },
      ])
      if (asistanDeposu.al().saltOkunur) inst.updateInputIsDisabled(true)
    },
    renderUserDefinedResponse: ozelYanit,
    renderCustomMessageFooter: ALTBILGI,
    renderCustomRequestFooter: (_slot, mesaj) => <IstekEkleri mesajId={mesaj.id} />,
    renderWriteableElements: {
      workspacePanelElement: <KaynakPaneli inst={() => instance.current} />,
      headerFixedActionsElement: <AiAciklama ogretmenAdi={secili?.ogretmen_adi ?? null} />,
      // Öğretmen seçimi başlığın altındaki satırda, tek kontrol (sohbet panelinin içinde ama AI yüzeyi değil: nötr).
      headerBottomElement: <OgretmenSecimi liste={ogretmen.liste} secili={ogretmen.id}
        onSec={id => void ogretmenSec(id)} hata={ogretmen.hata ? VOICE[okur].ogretmenHata : null} />,
      beforeInputElement: <><Karsilama inst={() => instance.current} karsilama={karsilama} hizliSorular={hizliSorular} />
        <GirisUyarisi /><BaglamCipi /><GirisEkleri /></>,
      promptLineActionsEnd: <GirisEylemleri inst={() => instance.current}
        mikrofon={{ var: ses.mikrofonVar, dinliyor: ses.dinliyor, bas: ses.mikrofon }} />,
      promptLineSendButtonStart: <GirisDugmeleri />,
      historyPanelElement: <GecmisPaneli depo={sohbet} ogrenci={ogrenci} inst={() => instance.current} ogretmenSec={ogretmen.sec} />,
    },
  }
  const sesOnay = { acik: ses.onayAcik, onayla: ses.onayla, vazgec: ses.vazgec, hata: ses.hata }
  const hazir = useKatexHazir()
  return { props, hazir, instance, ogretmen, ogretmenSec, sohbet, bicim, ses, sesOnay }
}
