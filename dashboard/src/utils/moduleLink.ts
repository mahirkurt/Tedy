// A module citation carries only slug and version (plan SP5 K-S9). The link goes to the
// dashboard's own module route, which fetches a viewing ticket when it opens (spec §5.4); the
// Assistant never hands out a modul.tedy.online URL. The locator arrives off the wire unchecked,
// so it has to pass the catalog's own rules (src/module_store.py) before it becomes an href.
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const SLUG_MAX = 60
const RESERVED = new Set(['taslak'])
const VERSION_MAX = 9999

export function moduleRoute(locator: Record<string, unknown> | null | undefined): string | null {
  const slug = locator?.slug
  const version = locator?.version
  if (typeof slug !== 'string' || slug.length > SLUG_MAX || !SLUG.test(slug) || RESERVED.has(slug)) return null
  if (typeof version !== 'number' || !Number.isInteger(version) || version < 1 || version > VERSION_MAX) return null
  return `/moduller/${slug}/v${version}`
}

export type ArsivYonu = { tur: 'yonlendir'; yol: string } | { tur: 'yayinda_degil' }

/** An archived version's ticket answers 410 `{arsivlendi: true, guncel}` (2026-10-24): the page moves to the
 * current version, replacing the old address in history, or says the module is no longer published. Anything
 * else is not an archive answer (null) and keeps the generic error sentence. */
export function arsivYonu(slug: string, version: number, body: unknown): ArsivYonu | null {
  if (typeof body !== 'object' || body === null || (body as { arsivlendi?: unknown }).arsivlendi !== true) return null
  const guncel = (body as { guncel?: unknown }).guncel
  const yol = guncel !== version ? moduleRoute({ slug, version: guncel }) : null
  return yol ? { tur: 'yonlendir', yol } : { tur: 'yayinda_degil' }
}
