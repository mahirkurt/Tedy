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
