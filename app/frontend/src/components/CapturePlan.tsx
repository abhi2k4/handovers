import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { Card, CardHeader, Chip } from './ui'

interface PlanItem {
  kind: 'question' | 'extra' | 'intro' | 'shadow' | 'access' | 'exit' | 'walkthrough'
  title: string
  detail: string
  tab: string
}

interface Plan {
  days_left: number
  pace: number
  covered: boolean
  message: string
  days: { offset: number; date: string; items: PlanItem[]; last: boolean }[]
}

const KIND: Record<PlanItem['kind'], { label: string; tone: 'risk' | 'soon' | 'ok' | 'idle' | 'accent' }> = {
  question: { label: 'Answer', tone: 'accent' },
  extra: { label: 'Extra', tone: 'idle' },
  intro: { label: 'Introduce', tone: 'ok' },
  shadow: { label: 'Do together', tone: 'ok' },
  walkthrough: { label: 'Walk through', tone: 'ok' },
  access: { label: 'Access', tone: 'risk' },
  exit: { label: 'Last day', tone: 'soon' },
}

/**
 * The days left, day by day: what to capture from the leaver and when, so the notice period is
 * used rather than left to the last week. Built by the backend from the graph
 * (services/handover_rules.capture_plan).
 */
export function CapturePlan({ hid, onOpen, compact = false }: { hid: string; onOpen?: (tab: string) => void; compact?: boolean }) {
  const { data: plan } = useApi<Plan>(`/handovers/${encodeURIComponent(hid)}/capture-plan`)
  const [all, setAll] = useState(false)
  if (!plan) return null
  const days = all ? plan.days : plan.days.slice(0, compact ? 4 : 6)
  return (
    <Card>
      <CardHeader
        title={plan.days_left === 0 ? 'Last day' : `The last ${plan.days_left} days`}
        right={plan.covered ? <Chip tone="ok">Required answers in</Chip> : plan.pace ? <span className="num">About {plan.pace} answers a day</span> : undefined}
      />
      <p className="-mt-2 mb-4 text-[14px] text-ink-2">{plan.message}</p>
      <ol className="relative flex flex-col">
        {days.map((d, i) => (
          <li key={d.offset} className="grid grid-cols-[64px_minmax(0,1fr)] gap-4">
            <div className="relative pt-0.5 text-right">
              <span className={`num text-[13px] ${d.offset === 0 ? 'font-semibold text-ink' : 'text-ink-3'}`}>{d.offset === 0 ? 'Today' : d.date}</span>
            </div>
            <div className={`relative border-l pb-4 pl-4 ${i === days.length - 1 ? 'border-transparent' : 'border-line'}`}>
              <span className={`absolute top-1.5 -left-[5px] size-[9px] rounded-full ${d.last ? 'bg-soon-fill' : d.offset === 0 ? 'bg-accent-fill' : 'bg-strong'}`} />
              <ul className="flex flex-col gap-1.5">
                {d.items.map((it, n) => (
                  <li key={`${it.kind}-${n}`}>
                    <button
                      onClick={() => onOpen?.(it.tab)}
                      disabled={!onOpen}
                      className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-[4px] px-1.5 py-0.5 text-left enabled:hover:bg-app"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-[14px]">{it.title}</span>
                        <span className="block truncate text-[12px] text-ink-3">{it.detail}</span>
                      </span>
                      <Chip tone={KIND[it.kind].tone}>{KIND[it.kind].label}</Chip>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </li>
        ))}
      </ol>
      {plan.days.length > days.length && (
        <button onClick={() => setAll(true)} className="ml-[80px] text-[13px] text-accent hover:underline">
          Show the whole plan · {plan.days.length - days.length} more days, to the last day
        </button>
      )}
    </Card>
  )
}
