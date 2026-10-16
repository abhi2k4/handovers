import { ErrorNote, Loading } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import type { InterviewKit } from '../../types/api'

export function InterviewKitView({ id }: { id: string }) {
  const { data: kit, error, loading } = useApi<InterviewKit>(`/handovers/${encodeURIComponent(id)}/artifacts/interview-kit`)
  if (loading && !kit) return <Loading label="Preparing questions" />
  if (error || !kit) return <ErrorNote message={error ?? 'Failed'} />

  return (
    <div>
      <p className="mb-8 max-w-[38rem] text-[16px] leading-6 text-ink-2">
        Questions anyone can ask, grounded in the work this role really does. Listen for the first list; the second is a
        reason to probe.
      </p>
      <ol className="border-t border-line">
        {kit.questions.map((q, i) => (
          <li key={q.id} className="grid gap-x-6 border-b border-line py-6 md:grid-cols-[28px_minmax(0,1fr)]">
            <span className="num text-[14px] text-ink-3">{i + 1}</span>
            <div>
              <div className="mb-1.5 text-[13px] text-ink-3">{q.skill}</div>
              <p className="max-w-[40rem] text-[16px] leading-6 font-medium tracking-[-0.005em]">{q.question}</p>
              <div className="mt-4 grid max-w-[40rem] gap-6 sm:grid-cols-2">
                <div>
                  <div className="mb-1 text-[13px] text-ink-3">Good answers mention</div>
                  <ul className="flex flex-col gap-1 text-[14px]">
                    {q.listen_for.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="mb-1 text-[13px] text-risk-text">Probe further if</div>
                  <ul className="flex flex-col gap-1 text-[14px] text-ink-2">
                    {q.red_flags.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
