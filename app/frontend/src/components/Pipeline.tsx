import { Check } from './icons'

export interface Stage {
  key: string
  label: string
  state: 'done' | 'current' | 'todo'
}

/**
 * The exit pipeline: Notice → Capture → Handover → Clearance → Exited. A segmented track: each
 * stage is a numbered cell over a bar that fills as the stage is done, so progress reads at a glance.
 */
export function Pipeline({ stages }: { stages: Stage[] }) {
  return (
    <ol className="grid min-w-[480px] flex-1 grid-flow-col gap-1 overflow-x-auto" style={{ gridAutoColumns: 'minmax(0,1fr)' }} aria-label="Exit stage">
      {stages.map((s, i) => (
        <li key={s.key} aria-current={s.state === 'current' ? 'step' : undefined} className="flex min-w-0 flex-col gap-1.5">
          <span
            aria-hidden
            className={`h-[3px] rounded-[1px] ${s.state === 'done' ? 'bg-ok' : s.state === 'current' ? 'bg-accent-fill' : 'bg-line'}`}
          />
          <span className="flex items-center gap-1.5 whitespace-nowrap">
            <span
              className={`flex size-4 items-center justify-center rounded-[2px] font-mono text-[10px] ${
                s.state === 'done' ? 'bg-ok text-white' : s.state === 'current' ? 'bg-accent-fill text-white' : 'text-ink-3 shadow-[inset_0_0_0_1px_var(--color-control)]'
              }`}
            >
              {s.state === 'done' ? <Check size={10} weight="bold" /> : i + 1}
            </span>
            <span className={`truncate text-[12.5px] ${s.state === 'current' ? 'font-semibold text-ink' : s.state === 'done' ? 'text-ink-2' : 'text-ink-3'}`}>{s.label}</span>
          </span>
        </li>
      ))}
    </ol>
  )
}

/** The current stage as one tag, for lists: a mini track plus the stage name. */
export function StageChip({ stages }: { stages: Stage[] }) {
  const current = stages.find((s) => s.state === 'current') ?? stages[stages.length - 1]
  return (
    <span className="inline-flex h-5 items-center gap-1.5 rounded-[2px] bg-page pr-1.5 pl-1.5 text-[11.5px] font-medium whitespace-nowrap text-ink shadow-[inset_0_0_0_1px_var(--color-control)]">
      <span className="flex gap-[2px]" aria-hidden>
        {stages.map((s) => (
          <span key={s.key} className={`h-2 w-[3px] rounded-[1px] ${s.state === 'done' ? 'bg-ok' : s.state === 'current' ? 'bg-accent-fill' : 'bg-line'}`} />
        ))}
      </span>
      {current.label}
    </span>
  )
}
