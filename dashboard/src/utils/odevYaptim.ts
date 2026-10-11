import type { HomeworkItem } from '../types'

/** The record both calls send: the stable key plus what identifies the row
 *  when the key is missing. */
function govde(hw: HomeworkItem) {
  return JSON.stringify({
    homework_key: hw.homework_key,
    'Ders Adı': hw['Ders Adı'],
    'Ödev Başlığı': hw['Ödev Başlığı'],
    'Ödev Son Teslim Tarihi': hw['Ödev Son Teslim Tarihi'],
  })
}

async function gonder(yol: string, hw: HomeworkItem): Promise<boolean> {
  try {
    const res = await fetch(yol, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: govde(hw),
    })
    if (!res.ok) return false
    window.dispatchEvent(new Event('tedy:homework-updated'))
    return true
  } catch {
    return false
  }
}

/** Records "Yaptım" for one piece of homework — the student's own mark,
 *  separate from the teacher's status, which only the portal sets.
 *
 *  Shared by İşler and Bugün so the two cannot send different records for the
 *  same action. Returns whether it was stored; on success every `useApi`
 *  reloads through `tedy:homework-updated`, so the work leaves the active
 *  lists wherever they are on screen. A failure is the caller's to say out
 *  loud (D3) — it used to be dropped silently on İşler. */
export function yaptimIsaretle(hw: HomeworkItem): Promise<boolean> {
  return gonder('/api/homework/mark-done', hw)
}

/** Takes a "Yaptım" back (talimatname S40, B63): a low-impact action is done
 *  without asking and undone on the same line. Same record, same reload; the
 *  server is idempotent, so a second tap is harmless. */
export function yaptimGeriAl(hw: HomeworkItem): Promise<boolean> {
  return gonder('/api/homework/unmark-done', hw)
}
