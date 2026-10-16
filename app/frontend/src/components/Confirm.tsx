import { useState } from 'react'
import type { ReactNode } from 'react'
import { AlertTriangle } from './icons'
import { ApiError } from '../lib/api'
import { Button, Modal } from './ui'

/**
 * Run an action the server may want confirmed first (it answers 409 with `confirm`): show its
 * message, and run again with `confirmed = true` if the person agrees.
 *
 *   const { run, dialog } = useConfirmable()
 *   run((confirmed) => api.post('/handovers', { ..., confirmed }))
 */
export function useConfirmable() {
  const [pending, setPending] = useState<{ message: string; retry: () => Promise<unknown>; cancel: () => void } | null>(null)
  const [busy, setBusy] = useState(false)

  async function run<T>(action: (confirmed: boolean) => Promise<T>): Promise<T | undefined> {
    try {
      return await action(false)
    } catch (e) {
      if (e instanceof ApiError && e.confirm) {
        return new Promise<T | undefined>((resolve, reject) => {
          setPending({
            message: e.confirm!.message,
            retry: () => action(true).then(resolve, reject),
            cancel: () => resolve(undefined),
          })
        })
      }
      throw e
    }
  }

  function close() {
    pending?.cancel()
    setPending(null)
  }

  const dialog: ReactNode = pending && (
    <Modal
      title="Are you sure?"
      onClose={close}
      footer={
        <>
          <Button variant="ghost" onClick={close} disabled={busy}>
            Choose someone else
          </Button>
          <Button
            disabled={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await pending.retry()
              } finally {
                setBusy(false)
                setPending(null)
              }
            }}
          >
            {busy ? 'Saving…' : 'Yes, continue'}
          </Button>
        </>
      }
    >
      <div className="flex gap-3 text-[14px] leading-5 text-ink-2">
        <AlertTriangle size={20} weight="duotone" className="mt-0.5 shrink-0 text-soon" />
        <p>{pending.message}</p>
      </div>
    </Modal>
  )

  return { run, dialog }
}
