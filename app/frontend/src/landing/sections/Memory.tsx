import { motion, useInView, useSpring, useTransform } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { QUESTIONS, type Outcome } from '../story'

const SETUPS = [
  { id: 'before', label: 'Before the handover' },
  { id: 'search', label: 'Search every document' },
  { id: 'handovers', label: 'With Handovers' },
] as const
type Setup = (typeof SETUPS)[number]['id']

// Before the handover the successor has nothing to search, so nothing is answered or leaked.
const outcome = (q: (typeof QUESTIONS)[number], s: Setup): Outcome =>
  s !== 'before' ? q[s] : q.handovers === 'withheld' ? 'withheld' : 'missed'

const ANSWERABLE = QUESTIONS.filter((q) => q.handovers === 'answered').length

function Count({ value }: { value: number }) {
  const spring = useSpring(value, { stiffness: 90, damping: 20 })
  const shown = useTransform(spring, (v) => Math.round(v))
  useEffect(() => spring.set(value), [spring, value])
  return <motion.span className="tabular-nums">{shown}</motion.span>
}

const STYLE: Record<Outcome, string> = {
  answered: 'text-white',
  missed: 'text-white/22',
  withheld: 'text-white/22 line-through decoration-white/30',
  leaked: 'text-[#ff8a7a]',
}

/** The committed benchmark, played out: the 18 questions a successor asks, lit when answered. */
export function Memory() {
  const ref = useRef<HTMLDivElement>(null)
  const seen = useInView(ref, { once: true, margin: '-30%' })
  const [setup, setSetup] = useState<Setup>('before')
  const [touched, setTouched] = useState(false)

  // Plays once on arrival: before, then search, then Handovers. A click takes over.
  useEffect(() => {
    if (!seen || touched) return
    const a = setTimeout(() => setSetup('search'), 900)
    const b = setTimeout(() => setSetup('handovers'), 3200)
    return () => {
      clearTimeout(a)
      clearTimeout(b)
    }
  }, [seen, touched])

  const outcomes = QUESTIONS.map((q) => outcome(q, setup))
  const answered = outcomes.filter((o) => o === 'answered').length
  const leaked = outcomes.filter((o) => o === 'leaked').length

  return (
    <section id="memory" data-snap="start" className="bg-dark py-28 text-white sm:py-36">
      <div ref={ref} className="wrap">
        <h2 className="serif h-hook text-center">
          A memory you
          <br className="max-sm:hidden" /> can check.
        </h2>
        <p className="mx-auto mt-6 max-w-[36rem] text-center text-[18px] leading-[1.6] text-white/60">
          The 18 questions a successor asks, answered three ways. Only the graph knows which figure is current and which
          note is private.
        </p>

        <div role="radiogroup" aria-label="Who answers" className="mx-auto mt-14 flex w-fit max-w-full gap-1 overflow-x-auto rounded-full bg-white/8 p-1 sm:mt-20">
          {SETUPS.map((s) => (
            <button
              key={s.id}
              role="radio"
              aria-checked={setup === s.id}
              onClick={() => {
                setTouched(true)
                setSetup(s.id)
              }}
              className="relative rounded-full px-4 py-2 text-[14px] font-medium whitespace-nowrap text-white/60 transition-colors hover:text-white aria-checked:text-ink sm:px-5"
            >
              {setup === s.id && (
                <motion.span layoutId="setup-pill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} className="absolute inset-0 rounded-full bg-white" />
              )}
              <span className="relative">{s.label}</span>
            </button>
          ))}
        </div>

        <p className="serif mt-12 text-center text-[clamp(2.25rem,4.4vw,3.75rem)] leading-[1.1] tracking-[-0.02em]">
          <Count value={answered} /> of {ANSWERABLE} answered
          <span className="text-white/35"> · </span>
          <span className={leaked ? 'text-[#ff8a7a]' : ''}>
            <Count value={leaked} /> private {leaked === 1 ? 'note' : 'notes'} leaked
          </span>
        </p>

        <p className="mx-auto mt-12 max-w-[62rem] text-center text-[17px] leading-[1.9] sm:text-[19px]">
          {QUESTIONS.map((q, i) => (
            <span key={q.q} className="inline-block">
              <span className={`transition-colors duration-700 ${STYLE[outcomes[i]]}`} style={{ transitionDelay: `${i * 35}ms` }}>
                {q.q}
              </span>
              {i < QUESTIONS.length - 1 && <span className="px-2 text-white/20">/</span>}
            </span>
          ))}
        </p>

      </div>
    </section>
  )
}
