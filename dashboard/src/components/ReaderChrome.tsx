import { Link } from 'react-router-dom'
import { Logout } from '@carbon/icons-react'
import Ornament from './Ornament'
import type { User } from '../hooks/useAuth'

/**
 * The reader's masthead.
 *
 * A reader account has no dashboard behind it — no sync health, no ödev camera,
 * no focus toggle — so it gets its own bar rather than the Carbon utility
 * header with most of its controls removed. Cloth ground, gold hairline and a
 * Plex Serif wordmark put the reading room's own binding on the top of the page.
 */
export default function ReaderHeader({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <header className="reader-header">
      <Link to="/kitaplar" className="reader-header__brand" aria-label="Tedy Books kitaplığı">
        <span className="reader-header__ornament" aria-hidden><Ornament variant="mark" /></span>
        <span className="reader-header__wordmark">Tedy Books</span>
      </Link>

      <div className="reader-header__side">
        <span className="reader-header__role">Okur</span>
        {user.picture && (
          <img
            src={user.picture}
            alt=""
            className="reader-header__avatar"
            referrerPolicy="no-referrer"
          />
        )}
        <span className="reader-header__identity">
          <strong className="reader-header__name">{user.name || user.email}</strong>
          <span className="reader-header__email">{user.email}</span>
        </span>
        <button
          type="button"
          className="reader-header__logout"
          onClick={onLogout}
          aria-label="Çıkış yap"
          title="Çıkış yap"
        >
          <Logout size={18} />
        </button>
      </div>
    </header>
  )
}

/**
 * Colophon rather than a corporate footer: the note a press leaves on the last
 * leaf, saying who set the book and in what.
 */
export function ReaderFooter() {
  return (
    <footer className="reader-footer">
      <span className="reader-footer__ornament" aria-hidden><Ornament /></span>
      <p className="reader-footer__line">
        Tedy Books · IBM Plex Serif ile dizildi
      </p>
    </footer>
  )
}
