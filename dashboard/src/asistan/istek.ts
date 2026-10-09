// İstek çalıştırma: sayfa, başlatıcı ve kartlar (Tekrar dene, Daha derine in) aynı yolu kullanır.
import type { ChatInstance, StreamChunk } from '@carbon/ai-chat'
import type { AssistantCitation } from '../types'
import { asistanDeposu } from './asistanDeposu.ts'
import { akisBaslat, hataYaniti, olayIsle, sonYanit } from './olayEslemesi.ts'
import type { HataKarti, SonYanitSecenekleri } from './olayEslemesi.ts'
import { okurHatasi, planGonder, soruGonder } from './akisIstemcisi.ts'

function secenekler(): SonYanitSecenekleri {
  const d = asistanDeposu.al()
  return { geriBildirim: !d.saltOkunur, ogrenci: d.okur === 'ogrenci' }
}

/** Bir isteği çalıştırır ve Carbon'a parça parça verir. Parçalar sırayla eklenir (addMessageChunk asenkron). */
export async function calistir(inst: ChatInstance, govde: Record<string, unknown>, plan: boolean, signal: AbortSignal) {
  asistanDeposu.ayarla({ yukleniyor: true })
  let d = akisBaslat(crypto.randomUUID())
  // Kısmi parçası Carbon'a gitmiş (açık, akan) mesaj: hata olursa yeni mesaj değil, bu mesaj hata kartıyla biter.
  let acikYanit: string | null = null
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
        if (r.kaldir) { const k = r.kaldir; sira(() => inst.messaging.removeMessages(k)); if (k.includes(acikYanit ?? '')) acikYanit = null }
        for (const p of r.parcalar) sira(() => inst.messaging.addMessageChunk(p))
        if (r.parcalar.length) acikYanit = 'final_response' in r.parcalar[r.parcalar.length - 1] ? null : d.yanitId
        if (o.ad === 'answer') {
          const payload = o.veri.payload as { answer?: string; meta?: { model?: string } }
          const dk = asistanDeposu.al()
          asistanDeposu.ayarla({ dokum: [...dk.dokum, { role: 'assistant', content: payload.answer ?? '' }],
            sonYanitId: d.yanitId, sonModel: payload.meta?.model })
        }
      }, signal)
      await zincir
    }
  } catch (e) {
    await zincir.catch(() => {})
    if ((e as { name?: string })?.name === 'AbortError' || signal.aborted) return
    const kart = hataYaniti(acikYanit ?? crypto.randomUUID(), okurHatasi(e), { govde, plan })
    if (acikYanit) await inst.messaging.addMessageChunk({ final_response: kart } as StreamChunk)
    else await inst.messaging.addMessage(kart)
  } finally {
    asistanDeposu.ayarla({ yukleniyor: false })
  }
}

/** Sohbet açılamadan düşen bir sorunun metnini baştan gönderen işlev (useAsistanSohbeti kurar): soru balonu
 *  zaten ekrandadır, yeniden gönderim yeni balon eklemez. */
let metinGonderici: ((inst: ChatInstance, metin: string, signal: AbortSignal) => Promise<void>) | null = null
export function metinGondericiKur(f: typeof metinGonderici) { metinGonderici = f }

/** Süren tekrar denemesi: Carbon'un durdur düğmesi (stopStreaming olayı) bunu da keser. */
let surenTekrar: AbortController | null = null
export function tekrariDurdur() { surenTekrar?.abort() }

export async function tekrarDene(inst: ChatInstance, hataMesajiId: string, kart: HataKarti) {
  if (!kart.govde && !kart.metin) return
  await inst.messaging.removeMessages([hataMesajiId])
  const denetim = new AbortController()
  surenTekrar = denetim
  // Carbon'un gönderiminin dışında koşar: yükleniyor göstergesi elle açılır (okur beklediğini görür).
  inst.updateIsMessageLoadingCounter('increase', 'Yeniden deneniyor…')
  asistanDeposu.ayarla({ tekrarSuruyor: true })
  try {
    if (kart.govde) await calistir(inst, kart.govde, kart.plan ?? false, denetim.signal)
    else if (kart.metin && metinGonderici) await metinGonderici(inst, kart.metin, denetim.signal)
  } finally {
    inst.updateIsMessageLoadingCounter('decrease')
    asistanDeposu.ayarla({ tekrarSuruyor: false })
    if (surenTekrar === denetim) surenTekrar = null
  }
}

export async function soruyuYeniden(inst: ChatInstance, metin: string, ek: { deep?: boolean; transient?: boolean; plan?: boolean }) {
  asistanDeposu.ayarla({ sonrakiIstek: ek })
  await inst.send(metin)
}


/** Kaynak ayrıntıları (figür küçük resmi, modül bağlantısı, kitap) workspace panelinde bugünkü SourcePanel ile. */
export async function kaynaklariAc(inst: ChatInstance, atiflar: AssistantCitation[], etkin: string | null, donus?: HTMLElement) {
  asistanDeposu.ayarla({ acikAtif: { atiflar, etkin, donus } })
  await inst.customPanels?.getPanel('workspace' as never).open({ title: 'Kaynaklar', preferredLocation: 'end' } as never)
}
