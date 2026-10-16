import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { ago } from '../lib/format'
import { Button, Card, CardHeader, Chip, Empty, TextArea } from './ui'

interface Note {
  id: string
  kind: 'note' | 'confirmation'
  text: string
  by_name: string
  at: number
}

/** HR's notes and confirmations on a handover (the approver's too). Never shown to the leaver. */
export function Notes({ hid, now }: { hid: string; now: number }) {
  const { data: notes, reload } = useApi<Note[]>(`/handovers/${encodeURIComponent(hid)}/notes`)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  async function add(kind: Note['kind']) {
    setBusy(true)
    try {
      await api.post(`/handovers/${encodeURIComponent(hid)}/notes`, { text, kind })
      setText('')
      reload()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Notes" meta={notes?.length || undefined} right="Not visible to the leaver" />
      <TextArea rows={2} placeholder="A note, or something you checked (e.g. laptop received at the front desk)" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="mt-2 flex gap-2">
        <Button variant="secondary" onClick={() => void add('note')} disabled={busy || text.trim().length < 2}>
          Add note
        </Button>
        <Button variant="ghost" onClick={() => void add('confirmation')} disabled={busy || text.trim().length < 2}>
          Add as confirmation
        </Button>
      </div>
      {notes && notes.length === 0 && <Empty>No notes yet.</Empty>}
      <ul className="mt-3 flex flex-col divide-y divide-line">
        {(notes ?? []).map((n) => (
          <li key={n.id} className="py-2.5">
            <div className="flex items-center gap-2 text-[13px] text-ink-3">
              <span className="font-medium text-ink-2">{n.by_name}</span>
              <span>{ago(n.at, now)}</span>
              {n.kind === 'confirmation' && <Chip tone="ok">Confirmed</Chip>}
            </div>
            <p className="mt-0.5 text-[14px] whitespace-pre-wrap">{n.text}</p>
          </li>
        ))}
      </ul>
    </Card>
  )
}
