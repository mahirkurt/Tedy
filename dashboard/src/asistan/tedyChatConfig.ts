import type { PublicConfig, PublicConfigMessaging } from '@carbon/ai-chat'
import { TURKCE } from './dilPaketi.ts'

export interface ConfigGirdisi {
  /** 'sayfa': /asistan'a gömülü (açık başlar, başlatıcı yok). 'panel': diğer sayfalarda başlatıcıyla açılan yan panel. */
  bicim: 'sayfa' | 'panel'
  okur: 'ogrenci' | 'aile'
  saltOkunur: boolean
  altBaslik: string
  gonder: PublicConfigMessaging['customSendMessage']
  gecmisYukle?: PublicConfigMessaging['customLoadHistory']
}

/** Sayfa ve başlatıcı aynı yapılandırmayı kullanır; farkları bileşen (ChatCustomElement / ChatContainer) yapar. */
export function tedyChatConfig(g: ConfigGirdisi): Omit<PublicConfig, 'markdown'> {
  return {
    // 'tr' paketin tarih yerel ayarlarında yok ve 'en'e (12 saat, "3:50 PM") düşüyor; 'en-gb' 24 saat verir.
    // Görünen metinler `strings` ile Türkçedir (Görev 1 raporu, 4. satır).
    locale: 'en-gb',
    strings: {
      ...TURKCE,
      input_placeholder: g.okur === 'ogrenci' ? 'Bir soru sor veya çalışma planı iste...' : 'Bir soru sorun veya çalışma planı isteyin...',
      // Soranın etiketi hitaba uyar (eski arayüzde VOICE): Işık'a "sen", aileye "siz".
      ...(g.okur === 'aile' ? { message_labelYou: 'Siz {timestamp}', messages_youSaid: 'Siz yazdınız' } : {}),
    },
    // Model cevabı ve alıntılanan portal metni ham HTML taşıyabilir: Carbon'un temizleyicisi açık (XSS).
    shouldSanitizeHTML: true,
    aiEnabled: true,
    assistantName: 'TEDY Asistan',
    hideAvatar: true,
    openChatByDefault: g.bicim === 'sayfa',
    launcher: { isOn: g.bicim === 'panel' },
    // Carbon'un başlık AI etiketi axe nested-interactive ihlali veriyor; açıklama kendi AILabel'ımızla (Görev 14).
    // Gömülü sayfada küçültülen sohbet geri açılamaz (başlatıcı kapalı, ölçüldü): küçült yalnız panelde.
    header: { title: 'TEDY Asistan', name: g.altBaslik, showAiLabel: false, showRestartButton: !g.saltOkunur,
      hideMinimizeButton: g.bicim === 'sayfa' },
    // Carbon'un başlangıç ekranı ayrı bir giriş alanı kullanır (yuvalar, mikrofon, ekler orada yok) ve yüklenen
    // geçmişte açık kalır: karşılama ve hızlı sorular eski arayüzdeki gibi tek giriş alanının üstünde (Karsilama.tsx).
    homescreen: { isOn: false },
    history: { isOn: true, showMobileMenu: true },
    upload: { isOn: false },   // ekler bugünkü çiplerle giriş üstü yuvada (Görev 16)
    layout: { showFrame: false, hasContentMaxWidth: true },
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
