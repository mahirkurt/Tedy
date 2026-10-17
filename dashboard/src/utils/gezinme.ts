// A link inside the dashboard opens in place (react-router) on a plain left click; a click that asks
// the browser for something else — a new tab or window (ctrl/cmd/shift/alt, middle button), a
// `target` other than _self — and any address outside the app (another origin, /api/ files) is left
// to the browser.

export interface TiklamaOlayi {
  button: number
  metaKey: boolean
  ctrlKey: boolean
  shiftKey: boolean
  altKey: boolean
  defaultPrevented: boolean
}

export function uygulamaIcindeAc(olay: TiklamaOlayi, href: string | null | undefined, target?: string | null): boolean {
  if (!href || olay.defaultPrevented || olay.button !== 0) return false
  if (olay.metaKey || olay.ctrlKey || olay.shiftKey || olay.altKey) return false
  if (target && target !== '_self') return false
  return href.startsWith('/') && !href.startsWith('//') && !href.startsWith('/api/')
}
