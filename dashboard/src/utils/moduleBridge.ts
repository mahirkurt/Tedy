export type ProgressEvent = 'answer' | 'segment_complete' | 'module_complete' | 'ready'

export interface ProgressMessage {
  type: 'edupedia:progress'
  v: 1
  slug: string
  version: number
  event: ProgressEvent
  xp: number
  ts: number
  segmentId?: string
  item?: number
  correct?: boolean
  attempts?: number
}

export interface RestoreState {
  answers: string[]
  done: string[]
  xp: number
}

const EVENTS = new Set<string>(['answer', 'segment_complete', 'module_complete', 'ready'])
const KEYS = new Set<string>(['type', 'v', 'slug', 'version', 'event', 'segmentId', 'item', 'correct', 'attempts', 'xp', 'ts'])
const SEGMENT_ID = /^[A-Za-z0-9_-]{1,64}$/
const isInt = (v: unknown, lo: number, hi: number): v is number =>
  typeof v === 'number' && Number.isInteger(v) && v >= lo && v <= hi

/**
 * Accept a progress message only from the module frame this page opened (spec §5.5).
 * The frame is sandboxed without allow-same-origin, so its origin is the string "null";
 * the source window, slug and version must all match what the iframe was opened with.
 * The server validates the same schema again — this check decides what is worth sending.
 */
export function acceptProgressMessage(
  event: Pick<MessageEvent, 'data' | 'origin' | 'source'>,
  frame: Window | null,
  slug: string,
  version: number,
): ProgressMessage | null {
  if (!frame || event.source !== frame || event.origin !== 'null') return null
  const d = event.data as Record<string, unknown> | null
  if (!d || typeof d !== 'object' || Array.isArray(d)) return null
  if (Object.keys(d).some(k => !KEYS.has(k))) return null
  if (d.type !== 'edupedia:progress' || d.v !== 1 || d.slug !== slug || d.version !== version) return null
  if (typeof d.event !== 'string' || !EVENTS.has(d.event)) return null
  if (!isInt(d.xp, 0, 1_000_000) || !isInt(d.ts, 1, 1e14)) return null
  if ((d.event === 'answer' || d.event === 'segment_complete')
      && (typeof d.segmentId !== 'string' || !SEGMENT_ID.test(d.segmentId))) return null
  if (d.event === 'answer'
      && (!isInt(d.item, 0, 999) || typeof d.correct !== 'boolean' || !isInt(d.attempts, 1, 99))) return null
  return d as unknown as ProgressMessage
}

export function restoreMessage(state: RestoreState) {
  return { type: 'edupedia:restore', v: 1, state } as const
}
