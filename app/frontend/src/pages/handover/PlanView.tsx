import { Printer } from '../../components/icons'
import { Button, ErrorNote, Loading } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { date } from '../../lib/format'
import type { Handover, Plan } from '../../types/api'

/** The handover (knowledge transfer) document: built from the graph, signed by three people. */
export function PlanView({ h }: { h: Handover }) {
  const { data: plan, error, loading } = useApi<Plan>(`/handovers/${encodeURIComponent(h.id)}/artifacts/plan`)
  if (loading && !plan) return <Loading />
  if (error || !plan) return <ErrorNote message={error ?? 'Failed'} />

  const facts = [
    ['Role', [h.title, h.team].filter(Boolean).join(', ')],
    ['Manager', h.manager ?? '–'],
    ['Last day', date(h.effective_at)],
    ['Handed to', h.successor ?? 'Not chosen yet'],
  ]
  const signers = [
    ['Prepared by', h.employee],
    ['Reviewed by', h.manager ?? 'Manager'],
    ['Received by', h.successor ?? 'Successor'],
  ]
  const sections = plan.sections.filter((s) => s.items.length > 0)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between print:hidden">
        <p className="text-[14px] text-ink-2">Written from {h.employee.split(' ')[0]}'s work. Ordered by what breaks first if forgotten.</p>
        <Button variant="secondary" onClick={() => window.print()}>
          <Printer size={15} /> Print or save as PDF
        </Button>
      </div>
      <article className="document rounded-[6px] bg-page p-8 shadow-card">
        <header className="mb-6 border-b border-line pb-5">
          <div className="text-[13px] font-medium text-ink-3">Handover document</div>
          <h2 className="mt-1 text-[22px] font-semibold tracking-[-0.01em]">{h.employee}</h2>
          <dl className="mt-3 grid grid-cols-2 gap-x-8 gap-y-1.5 text-[14px] sm:grid-cols-4">
            {facts.map(([k, v]) => (
              <div key={k}>
                <dt className="text-[12px] text-ink-3">{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </header>

        {sections.map((s, i) => (
          <section key={s.key} className="mb-6 break-inside-avoid">
            <h3 className="mb-2 text-[15px] font-semibold">
              <span className="num mr-2 text-ink-3">{i + 1}</span>
              {s.title}
              <span className="num ml-2 font-normal text-ink-3">{s.items.length}</span>
            </h3>
            <ul className="border-t border-line">
              {s.items.map((item) => (
                <li key={item.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-6 border-b border-line py-2.5">
                  <div className="min-w-0">
                    <div className="text-[14px] font-medium">{item.title}</div>
                    {item.detail && <p className="mt-0.5 text-[13px] leading-[18px] text-ink-2">{item.detail}</p>}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-0.5 text-right text-[13px]">
                    {item.overdue && <span className="text-risk-text">Overdue</span>}
                    {!item.overdue && item.due && <span className="num text-ink-3">Next {date(item.due, true)}</span>}
                    {item.status === 'answered' && <span className="text-ink-3">Captured</span>}
                    {item.status === 'open' && <span className="text-soon">Ask in exit interview</span>}
                    {item.receiver && <span className="text-ink-2">To {item.receiver.name}</span>}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}

        <footer className="mt-8 grid grid-cols-3 gap-6 text-[13px]">
          {signers.map(([role, name]) => (
            <div key={role}>
              <div className="mb-6 h-px bg-strong" />
              <div className="font-medium">{name}</div>
              <div className="text-ink-3">{role}</div>
            </div>
          ))}
        </footer>
      </article>
    </div>
  )
}
