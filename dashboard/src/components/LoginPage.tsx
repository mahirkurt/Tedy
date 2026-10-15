import { useEffect, useRef, useState } from 'react'
import { Button, InlineLoading, InlineNotification, SkeletonPlaceholder } from '@carbon/react'
import { useGsi } from '../hooks/useGsi'
import type { GirisSonucu } from '../hooks/useAuth'
import type { GirisBildirimi } from '../utils/girisHatasi'
import { gsiOlcusu } from '../utils/gsiDurumu'
import './LoginPage.scss'

// Giriş sayfası yenilemesi (2026-10-15): spec docs/superpowers/specs/2026-10-15-giris-sayfasi-yenileme-design.md.
// Carbon's login pattern, split-screen: a calm brand band and a form on one keyline of the 2x grid; every state
// of Google's script and of the sign-in is on the page in Turkish (D3, D4).

const GOOGLE_CLIENT_ID = '343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com'

/** The footer's year, read once when the bundle loads. */
const YIL = new Date().getFullYear()

interface LoginPageProps {
  onLogin: (credential: string) => Promise<GirisSonucu>
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const { durum, yenidenDene } = useGsi()
  const yuvaRef = useRef<HTMLDivElement>(null)
  const dugmeRef = useRef<HTMLDivElement>(null)
  const baslikRef = useRef<HTMLHeadingElement>(null)
  const [olcu, setOlcu] = useState<{ zoom: number; genislik: number } | null>(null)
  const [dogrulaniyor, setDogrulaniyor] = useState(false)
  const [hata, setHata] = useState<GirisBildirimi | null>(null)

  // Google's button is a px-drawn iframe: it follows the column's width and the root scale only if told
  // (spec §3.4). The observer's first call measures; later calls follow a resize.
  useEffect(() => {
    const yuva = yuvaRef.current
    if (!yuva) return
    const gozlemci = new ResizeObserver(() => {
      const kok = parseFloat(getComputedStyle(document.documentElement).fontSize)
      const yeni = gsiOlcusu(kok, yuva.clientWidth)
      setOlcu(o => (o && o.zoom === yeni.zoom && o.genislik === yeni.genislik ? o : yeni))
    })
    gozlemci.observe(yuva)
    return () => gozlemci.disconnect()
  }, [])

  useEffect(() => {
    if (durum !== 'hazir' || !window.google) return
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async ({ credential }) => {
        setHata(null)
        setDogrulaniyor(true)
        const sonuc = await onLogin(credential)
        // On success App replaces this page with the dashboard.
        if (!sonuc.ok) {
          setHata(sonuc.bildirim)
          setDogrulaniyor(false)
        }
      },
    })
  }, [durum, onLogin])

  useEffect(() => {
    if (durum !== 'hazir' || !olcu || !window.google || !dugmeRef.current) return
    window.google.accounts.id.renderButton(dugmeRef.current, {
      theme: 'outline',
      size: 'large',
      width: olcu.genislik,
      text: 'signin_with',
      shape: 'rectangular',
      locale: 'tr',
    })
  }, [durum, olcu])

  const tekrarDene = () => {
    yenidenDene()
    // The retry button leaves with the failure; focus goes to the page's heading, not to <body> ([3.8-8]).
    baslikRef.current?.focus()
  }

  const iskelet = durum === 'iskelet'
  const dugmeGorunur = durum === 'hazir' && !dogrulaniyor

  return (
    <div className="login-page">
      <header className="login-page__hero">
        <picture>
          {/* Windows high contrast paints the band in the system Canvas, usually
              white; the white logo vanished on it (2026-09-25). */}
          <source srcSet="/tedy-logo.svg" media="(forced-colors: active)" />
          <img src="/tedy-logo-white.svg" alt="TEDY" className="login-page__hero-logo" />
        </picture>
        <div className="login-page__hero-text">
          <p className="login-page__hero-school">TED Rönesans Koleji</p>
          <p className="login-page__hero-value">Okul günü tek bakışta.</p>
          <p className="login-page__hero-support">
            TEDY okulun portalını düzenli okur; dersi, ödevi ve sınavı sırayla önüne koyar.
          </p>
        </div>
      </header>

      {/* B40: the sign-in region is the page's main landmark (Carbon login: name the login region). */}
      <main className="login-page__main" aria-labelledby="giris-basligi">
        <div className="login-page__form">
          <h1 id="giris-basligi" ref={baslikRef} tabIndex={-1} className="login-page__title">TEDY'ye giriş yap</h1>
          <p className="login-page__intro">
            Derslerini, ödevlerini ve sınavlarını görmek için Google hesabınla devam et.
          </p>

          {hata && (
            <InlineNotification kind="error" role="alert" lowContrast hideCloseButton
              statusIconDescription="Hata" title={hata.baslik} subtitle={hata.metin}
              className="login-page__notification" />
          )}
          {durum === 'yuklenemedi' && (
            <InlineNotification kind="error" role="alert" lowContrast hideCloseButton
              statusIconDescription="Hata" title="Google düğmesi yüklenemedi"
              subtitle="Bir reklam engelleyici ya da ağ Google'ı durdurmuş olabilir. Bu sayfada engelleyiciyi kapatıp yeniden dene."
              className="login-page__notification" />
          )}
          {durum === 'gecikiyor' && (
            <InlineNotification kind="warning" role="status" lowContrast hideCloseButton
              statusIconDescription="Uyarı" title="Google düğmesi gecikiyor"
              subtitle="Bağlantın yavaş olabilir. Biraz bekle ya da yeniden dene."
              className="login-page__notification" />
          )}

          {/* One slot, one height: nothing below it moves while the button arrives (P8). */}
          <div ref={yuvaRef} className="login-page__gsi" aria-busy={iskelet || undefined}>
            {iskelet && <SkeletonPlaceholder className="login-page__gsi-iskelet" />}
            {(durum === 'gecikiyor' || durum === 'yuklenemedi') && (
              <Button kind="tertiary" size="lg" onClick={tekrarDene}>Yeniden dene</Button>
            )}
            {dogrulaniyor && (
              <InlineLoading status="active" description="Giriş yapılıyor…" iconDescription="Giriş yapılıyor" />
            )}
            {/* Google draws its iframe here; zoom is computed at run time (S5). */}
            <div ref={dugmeRef} className="login-page__gsi-dugme" hidden={!dugmeGorunur}
              style={olcu ? { zoom: olcu.zoom } : undefined} />
          </div>
          <p className="cds--visually-hidden login-page__durum" role="status">
            {iskelet ? 'Google giriş düğmesi yükleniyor' : ''}
          </p>

          <p className="login-page__helper">Yalnız ailenin tanımlı Google hesaplarıyla giriş yapılır.</p>
        </div>
      </main>

      <footer className="login-page__footer">
        {/* True to /api/auth/login: it keeps the e-mail, the name and the picture from Google's token. */}
        <p className="login-page__footer-text">
          Giriş Google ile yapılır; şifren TEDY'ye gelmez. TEDY bu girişten yalnız adını,{' '}
          <span className="login-page__nobr">e-posta</span> adresini ve profil fotoğrafını alır.
        </p>
        <p className="login-page__footer-text">TED Rönesans Koleji · {YIL}</p>
      </footer>
    </div>
  )
}
