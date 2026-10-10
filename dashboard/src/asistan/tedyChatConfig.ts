import type { PublicConfig, PublicConfigMessaging, ToolbarAction } from '@carbon/ai-chat'
import { AILE, TURKCE } from './dilPaketi.ts'

export interface ConfigGirdisi {
  /** 'sayfa': /asistan'a gömülü (açık başlar, başlatıcı yok). 'panel': diğer sayfalarda başlatıcıyla açılan yan panel. */
  bicim: 'sayfa' | 'panel'
  okur: 'ogrenci' | 'aile'
  saltOkunur: boolean
  /** Başlık: o anki öğretmenin adı ("Genel asistan", "Matematik öğretmeni"); ürün adı başlıkta tekrarlanmaz. */
  baslik: string
  /** Başlık çubuğunun kendi eylemleri ("Sohbetler", panelde "Tam ekran"); Carbon'un yeniden başlatı sonra gelir. */
  eylemler?: ToolbarAction[]
  gonder: PublicConfigMessaging['customSendMessage']
  gecmisYukle?: PublicConfigMessaging['customLoadHistory']
}

/** Mesaj sütunu ve geçmiş paneli rem ile: 4K'da kök yazı büyüdükçe sütun da büyür (B28; Carbon'un varsayılanı 672 px). */
export const MESAJ_GENISLIGI = '42rem'

/** Sayfa ve başlatıcı aynı yapılandırmayı kullanır; farkları bileşen (ChatCustomElement / ChatContainer) yapar. */
export function tedyChatConfig(g: ConfigGirdisi): Omit<PublicConfig, 'markdown'> {
  return {
    // 'tr' paketin tarih yerel ayarlarında yok ve 'en'e (12 saat, "3:50 PM") düşüyor; 'en-gb' 24 saat verir.
    // Görünen metinler `strings` ile Türkçedir (Görev 1 raporu, 4. satır).
    locale: 'en-gb',
    strings: {
      ...TURKCE,
      // "…" tek karakter (içerik kuralı [3.9-3]).
      input_placeholder: g.okur === 'ogrenci' ? 'Bir soru sor ya da çalışma planı iste…' : 'Bir soru sorun ya da çalışma planı isteyin…',
      // Hitap (eski arayüzde VOICE): Işık'a "sen", aileye "siz" — soranın etiketi ve cümle biçimli metinler.
      ...(g.okur === 'aile' ? AILE : {}),
    },
    // Model cevabı ve alıntılanan portal metni ham HTML taşıyabilir: Carbon'un temizleyicisi açık (XSS).
    shouldSanitizeHTML: true,
    // S46: sohbet paneli Carbon'un AI yüzeyidir (degrade yüzey başına); panelin dışındaki TEDY öğeleri nötr kalır.
    aiEnabled: true,
    assistantName: 'TEDY Asistan',
    hideAvatar: true,
    openChatByDefault: g.bicim === 'sayfa',
    launcher: { isOn: g.bicim === 'panel' },
    // Başlık o anki öğretmendir; `name` boş (ürün adı tekrarlanmaz). Carbon'un başlık AI etiketi axe
    // nested-interactive ihlali veriyor (2026-10-10 yeniden ölçüldü); açıklama kendi AILabel'ımızla (AiAciklama).
    // Gömülü sayfada küçültülen sohbet geri açılamaz (başlatıcı kapalı, ölçüldü): küçült yalnız panelde.
    header: { title: g.baslik, showAiLabel: false, showRestartButton: !g.saltOkunur,
      hideMinimizeButton: g.bicim === 'sayfa', ...(g.eylemler?.length ? { actions: g.eylemler } : {}) },
    // Carbon'un başlangıç ekranı ayrı bir giriş alanı kullanır (yuvalar, mikrofon, ekler orada yok) ve yüklenen
    // geçmişte açık kalır: karşılama ve hızlı sorular tek giriş alanının üstünde (Karsilama.tsx).
    homescreen: { isOn: false },
    // Geçmiş kapalı başlar ve başlıktaki "Sohbetler" eylemiyle açılır (masaüstünde de); Carbon'un mobil menüsü
    // ("≡") kapalı: aynı iş için ikinci yol yok.
    history: { isOn: true, showMobileMenu: false, startClosed: true },
    upload: { isOn: false },   // ekler giriş satırının kendi eylemleriyle (GirisDugmeleri.tsx)
    // Genişletilmiş giriş: yazı alanı kendi satırında, eylemler (ek, ödev, ses, plan) altında, gönder sağda —
    // telefonda yazı alanı daralmadan 48 px'lik eylemler sığar (PROMPT_LINE_ACTIONS_END yuvası yalnız bu düzende var).
    input: { expanded: true },
    layout: { showFrame: false, hasContentMaxWidth: true, customProperties: { 'messages-max-width': MESAJ_GENISLIGI } },
    messaging: {
      customSendMessage: g.gonder,
      ...(g.gecmisYukle ? { customLoadHistory: g.gecmisYukle } : {}),
      messageTimeoutSecs: 180, showStopButtonImmediately: true, skipWelcome: true,
    },
    isReadonly: g.saltOkunur,
    persistFeedback: true,
    // injectCarbonTheme verilmez: Carbon temayı kendi kabına yazınca öğretmen modunun ders rengini eziyordu (ölçüldü);
    // pano zaten g10 teması altında, token'lar sayfadan miras gelir.
    keyboardShortcuts: { messageFocusToggle: { isOn: true } },
  }
}
