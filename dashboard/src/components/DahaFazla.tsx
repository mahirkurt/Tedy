import { useContext } from 'react'
import { Link } from 'react-router-dom'
import { SessionContext } from '../contexts/session'
import { routes, secondaryNavRoutes } from '../routes'

// "Daha fazla" (D3a): the phone's fifth tab lands here. The list is derived from
// the same route table as the side nav, so a page added there appears here
// without a second edit. Tedy Books joins it: on a phone the four daily tabs
// are Bugün, İşler, Asistan, Dersler (user's choice, 2026-10-02).
export default function DahaFazla() {
  // App renders pages only inside SessionContext.Provider with a signed-in user.
  const user = useContext(SessionContext)!
  const kitaplar = routes.find(r => r.path === '/kitaplar')
  const liste = [...(kitaplar ? [kitaplar] : []), ...secondaryNavRoutes(user.role)]
  return (
    <section className="daha-fazla" aria-labelledby="daha-fazla-baslik">
      <h2 id="daha-fazla-baslik" className="daha-fazla__baslik">Daha fazla</h2>
      <ul className="daha-fazla__liste">
        {liste.map(r => {
          const Icon = r.icon
          return (
            <li key={r.path}>
              <Link to={r.path} className="daha-fazla__oge">
                <Icon aria-hidden="true" />
                <span>{r.label}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
