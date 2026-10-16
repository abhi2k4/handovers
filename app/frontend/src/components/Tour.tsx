import { ArrowRightLeft, BarChart3, Brain, MessageSquareText, Network, UserRound, X } from './icons'
import type { ComponentType } from 'react'
import { useEffect, useState } from 'react'
import { TOUR_SEEN } from '../hooks/useTour'
import { Button } from './ui'

type Icon = ComponentType<{ size?: number; strokeWidth?: number; className?: string }>

const STEPS: { icon: Icon; title: string; body: string; points?: string[] }[] = [
  {
    icon: Brain,
    title: 'People leave. Their context shouldn’t.',
    body: 'Handovers keeps a memory of everyone’s work, learned from tickets, pull requests, daily reports, messages and documents. When someone resigns, it hands HR and the successor what that person knew.',
  },
  {
    icon: Network,
    title: 'The graph does the thinking',
    body: 'Every person, task, account, decision and source is a node in FalkorDB. Graph queries answer what an LLM cannot:',
    points: [
      'What does only this person know or control?',
      'Which settings have no recorded reason?',
      'Where did this answer come from, and who approved it?',
    ],
  },
  {
    icon: UserRound,
    title: 'Pick who you are',
    body: 'Use “View as” at the bottom of the sidebar. Each person sees a different app, and the backend enforces it:',
    points: [
      'Meera (HR) runs the handover but cannot read answers',
      'Nisha (leaving) answers only what nothing else explains',
      'Aditi (manager) is the only one who can approve',
      'Ananya (successor) asks the companion',
    ],
  },
  {
    icon: ArrowRightLeft,
    title: 'The handover, step by step',
    body: 'HR opens a handover and gets a job description written from the real work, a screening kit, an interview kit and a plan ordered by what breaks first. The leaver answers a few targeted questions; the manager approves what moves.',
  },
  {
    icon: MessageSquareText,
    title: 'The successor asks',
    body: 'Before the transfer, the companion says it does not know. After the manager approves, it answers from the inherited memory and cites the source and who approved it. It never guesses.',
  },
  {
    icon: BarChart3,
    title: 'Try the 3-minute demo',
    body: 'Follow the story:',
    points: [
      'View as Kavya: Insights, what is held by one person',
      'View as Nisha: answer a question, confirm it',
      'View as Ananya: ask “What is our CAC target and why?”',
      'View as Aditi: approve the transfer',
      'View as Ananya: ask again and see the cited answer',
    ],
  },
]

/** First-visit guide; reopen it from the sidebar. */
export function Tour({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [i, setI] = useState(0)
  const last = i === STEPS.length - 1
  const close = () => {
    try {
      localStorage.setItem(TOUR_SEEN, '1')
    } catch {
      // storage unavailable: the tour may show again next visit
    }
    setI(0)
    onClose()
  }

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
      if (e.key === 'ArrowRight') setI((n) => Math.min(n + 1, STEPS.length - 1))
      if (e.key === 'ArrowLeft') setI((n) => Math.max(n - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (!open) return null
  const step = STEPS[i]
  const Icon = step.icon

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4 backdrop-blur-[2px]" onClick={close}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-title"
        className="w-full max-w-[460px] rounded-[8px] bg-page p-6 shadow-[0_0_0_1px_var(--color-line),0_24px_48px_-12px_rgba(15,27,45,0.25)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between">
          <span className="flex size-10 items-center justify-center rounded-[6px] bg-accent-soft text-accent">
            <Icon size={20} strokeWidth={1.75} />
          </span>
          <button onClick={close} aria-label="Close guide" className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-ink">
            <X size={16} />
          </button>
        </div>

        <h2 id="tour-title" className="text-[18px] leading-6 font-semibold tracking-[-0.01em]">
          {step.title}
        </h2>
        <p className="mt-2 text-[14px] leading-5 text-ink-2">{step.body}</p>
        {step.points && (
          <ul className="mt-3 flex flex-col gap-1.5">
            {step.points.map((p) => (
              <li key={p} className="flex gap-2 text-[14px] leading-5 text-ink-2">
                <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-accent-fill" />
                {p}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-6 flex items-center justify-between">
          <div className="flex gap-1.5" aria-label={`Step ${i + 1} of ${STEPS.length}`}>
            {STEPS.map((s, n) => (
              <button
                key={s.title}
                onClick={() => setI(n)}
                aria-label={`Go to step ${n + 1}`}
                className={`h-1.5 rounded-full transition-all duration-200 ${n === i ? 'w-5 bg-accent-fill' : 'w-1.5 bg-control hover:bg-strong'}`}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {!last && (
              <Button variant="ghost" onClick={close}>
                Skip tour
              </Button>
            )}
            {i > 0 && (
              <Button variant="secondary" onClick={() => setI(i - 1)}>
                Back
              </Button>
            )}
            <Button onClick={() => (last ? close() : setI(i + 1))}>{last ? 'Start exploring' : 'Next'}</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
