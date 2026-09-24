import type { HomeworkItem } from '../types'

/** Records "Yaptım" for one piece of homework — the student's own mark,
 *  separate from the teacher's status, which only the portal sets.
 *
 *  Shared by İşler and Bugün so the two cannot send different records for the
 *  same action. Returns whether it was stored; on success every `useApi`
 *  reloads through `tedy:homework-updated`, so the work leaves the active
 *  lists wherever they are on screen. A failure is the caller's to say out
 *  loud (D3) — it used to be dropped silently on İşler. */
export async function yaptimIsaretle(hw: HomeworkItem): Promise<boolean> {
  try {
    const res = await fetch('/api/homework/mark-done', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        homework_key: hw.homework_key,
        'Ders Adı': hw['Ders Adı'],
        'Ödev Başlığı': hw['Ödev Başlığı'],
        'Ödev Son Teslim Tarihi': hw['Ödev Son Teslim Tarihi'],
      }),
    })
    if (!res.ok) return false
    window.dispatchEvent(new Event('tedy:homework-updated'))
    return true
  } catch {
    return false
  }
}
