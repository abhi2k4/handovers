import { useState } from 'react'
import { Button, Modal, TextArea } from '../../components/ui'
import { api } from '../../lib/api'
import { date } from '../../lib/format'
import type { Handover } from '../../types/api'

/** Withdraw a resignation, within the company's window. Says until when, and asks why. */
export function CancelHandover({ h, onDone }: { h: Handover; onDone: () => void }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const window = h.cancel
  if (!window || !h.can?.run || h.status === 'cancelled' || h.status === 'transferred') return null

  async function cancel() {
    setBusy(true)
    setError('')
    try {
      await api.post(`/handovers/${encodeURIComponent(h.id)}/cancel`, { reason })
      setOpen(false)
      onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  if (!window.allowed)
    return (
      <span className="text-[13px] text-ink-3" title={window.reason}>
        Withdrawal window closed{window.until ? ` ${date(window.until, true)}` : ''}
      </span>
    )

  return (
    <>
      <Button variant="ghost" onClick={() => setOpen(true)} className="text-[13px]">
        Cancel handover
        {window.until && <span className="font-normal text-ink-3">· until {date(window.until, true)}</span>}
      </Button>
      {open && (
        <Modal
          title={`Cancel ${h.employee.split(' ')[0]}'s handover?`}
          description={
            window.until
              ? `Company policy allows withdrawing a resignation until ${date(window.until, true)}. The handover stops; everything captured so far stays in the graph.`
              : undefined
          }
          onClose={() => setOpen(false)}
          footer={
            <>
              {error && <span className="mr-auto text-[13px] text-risk-text">{error}</span>}
              <Button variant="ghost" onClick={() => setOpen(false)} disabled={busy}>
                Keep it
              </Button>
              <Button onClick={cancel} disabled={busy || reason.trim().length < 5} className="bg-risk hover:bg-risk-text">
                {busy ? 'Cancelling…' : 'Cancel handover'}
              </Button>
            </>
          }
        >
          <label className="flex flex-col gap-1.5 text-[14px]">
            <span className="font-medium">Reason</span>
            <TextArea rows={3} placeholder="For example: resignation withdrawn after a counter-offer, 14 Oct" value={reason} onChange={(e) => setReason(e.target.value)} />
            <span className="text-[13px] text-ink-3">{h.employee}, their manager and the successor are told.</span>
          </label>
        </Modal>
      )}
    </>
  )
}
