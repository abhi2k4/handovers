import { motion, useTransform, type MotionValue } from 'framer-motion'
import { GLYPHS } from '../../components/platformGlyphs'
import wall from '../art/saffron-wall.webp'
import type { ReactNode } from 'react'
import { Reveal } from '../components/Plate'
import { Scene } from '../components/Scene'

/** A WhatsApp business message with reply buttons, as HR receives it. */
function WhatsAppMessage() {
  return (
    <div className="font-system w-full">
      <div className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold text-black/60">
        <svg viewBox="0 0 24 24" className="size-3.5" aria-hidden>
          <path fill="currentColor" d={GLYPHS.whatsapp[1]} />
        </svg>
        Handovers
      </div>
      <div className="overflow-hidden rounded-[14px] rounded-tl-[4px] bg-white shadow-shot">
        <div className="px-3.5 pt-3 pb-2">
          <div className="text-[14px] font-semibold text-black">Nisha Verma resigned</div>
          <p className="mt-1 text-[13.5px] leading-[1.4] text-black/80">
            Last day 3 Nov, in 22 days. She is the only admin on Meta Business Manager, Mixpanel and Google Analytics.
          </p>
          <div className="mt-1 text-right text-[11px] text-black/40">10:42</div>
        </div>
        {['Open handover', 'Remind the manager'].map((b) => (
          <div key={b} className="border-t border-black/8 py-2.5 text-center text-[14px] font-medium text-[#0a84c6]">
            {b}
          </div>
        ))}
      </div>
    </div>
  )
}

const CLEARANCE = [
  'Second admin on Meta Business Manager',
  'Second admin on the GA4 property',
  'Mixpanel workspace to Ananya',
  'New owner: daily budget pacing',
  'New owner: the UTM sheet',
  'Handover document signed',
  'Laptop returned',
]

function Tick({ label, t, p }: { label: string; t: number; p: MotionValue<number> }) {
  const on = useTransform(p, [t, t + 0.015], [0, 1])
  const fill = useTransform(on, [0, 1], ['rgba(12,122,77,0)', 'rgba(12,122,77,1)'])
  const ring = useTransform(on, [0, 1], ['rgba(22,24,29,0.2)', 'rgba(12,122,77,1)'])
  return (
    <li className="flex items-center gap-3 border-t border-black/6 py-2.5 first:border-t-0">
      <motion.span style={{ backgroundColor: fill, borderColor: ring }} className="flex size-[18px] shrink-0 items-center justify-center rounded-full border-[1.5px]">
        <motion.svg style={{ opacity: on }} viewBox="0 0 12 12" className="size-2.5 text-white" aria-hidden>
          <path d="M2.5 6.2 5 8.5l4.5-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
      </motion.span>
      <span className="text-[13.5px] text-black/85">{label}</span>
    </li>
  )
}

/** Clearance ticks itself off as the notice period runs. */
function Clearance({ p }: { p: MotionValue<number> }) {
  const done = useTransform(p, (v) => CLEARANCE.filter((_, i) => v >= 0.4 + i * 0.03).length)
  return (
    <div className="font-system w-full rounded-[14px] bg-white p-4 shadow-shot">
      <div className="flex items-baseline justify-between">
        <span className="text-[14px] font-semibold text-black">Clearance</span>
        <span className="text-[12px] text-black/45 tabular-nums">
          <motion.span>{done}</motion.span> of {CLEARANCE.length}
        </span>
      </div>
      <ul className="mt-2">
        {CLEARANCE.map((c, i) => (
          <Tick key={c} label={c} t={0.4 + i * 0.03} p={p} />
        ))}
      </ul>
    </div>
  )
}

/** The successor asks; the answer cites whose work it came from. */
function Answer() {
  return (
    <div className="font-system flex w-full flex-col gap-2.5">
      <div className="self-end rounded-[16px] rounded-br-[4px] bg-ink px-3.5 py-2.5 text-[14px] text-white shadow-shot">
        Why did we shift budget to Reels?
      </div>
      <div className="rounded-[16px] rounded-bl-[4px] bg-white p-3.5 shadow-shot">
        <p className="text-[14px] leading-[1.45] text-black/85">
          In the March tests, Reels CPM was 40% lower than feed placements, so 30% of paid social moved there.
        </p>
        <div className="mt-3 border-t border-black/8 pt-2.5 text-[12px] text-black/50">From Nisha&rsquo;s Q2 growth plan · April</div>
      </div>
    </div>
  )
}

const MOMENTS = [
  { date: '12 Oct', title: 'The day she resigns', text: 'HR and the manager hear on WhatsApp, with what is at risk.' },
  { date: '13 Oct – 3 Nov', title: 'The notice period', text: 'Clearance, the handover and the letters fill themselves in.' },
  { date: '4 Nov', title: 'The successor’s first day', text: 'Ask anything. Every answer names its source.' },
]
// Where each moment is fully on stage, as scroll progress.
const CUT = [0.3, 0.66]

/** Scroll offsets and values for moment i: fades in after the cut before it, out before the cut after it. */
function band(i: number, off: number, on: number): [number[], number[]] {
  const fadeIn = i > 0 ? [CUT[i - 1] - 0.04, CUT[i - 1] + 0.02] : []
  const fadeOut = i < CUT.length ? [CUT[i] - 0.02, CUT[i] + 0.04] : []
  return [
    [...fadeIn, ...fadeOut],
    [...(fadeIn.length ? [off, on] : []), ...(fadeOut.length ? [on, off] : [])],
  ]
}

function Stage({ i, p, children }: { i: number; p: MotionValue<number>; children: ReactNode }) {
  const opacity = useTransform(p, ...band(i, 0, 1))
  const [at, ys] = band(i, 40, 0)
  const y = useTransform(p, at, i === 0 ? ys.map((v) => -v) : i === 2 ? ys : [40, 0, 0, -40])
  return (
    <motion.div style={{ opacity, y }} className="absolute inset-0 flex items-center justify-center p-5">
      <div className="w-full max-w-[340px]">{children}</div>
    </motion.div>
  )
}

function Stop({ i, p }: { i: number; p: MotionValue<number> }) {
  const opacity = useTransform(p, ...band(i, 0.32, 1))
  const m = MOMENTS[i]
  return (
    <motion.div style={{ opacity }} className="min-w-0 flex-1 pt-4">
      <div className="text-[13px] text-ink-3 tabular-nums">{m.date}</div>
      <h3 className="serif mt-1 text-[24px] leading-tight sm:text-[28px]">{m.title}</h3>
      <p className="mt-1.5 max-w-[22rem] text-[15px] leading-[1.55] text-ink-2">{m.text}</p>
    </motion.div>
  )
}

/** On phones only one stop fits: its words swap in place. */
function MobileStop({ p }: { p: MotionValue<number> }) {
  const i = useTransform(p, (v) => (v < CUT[0] ? 0 : v < CUT[1] ? 1 : 2))
  const date = useTransform(i, (k) => MOMENTS[k].date)
  const title = useTransform(i, (k) => MOMENTS[k].title)
  const text = useTransform(i, (k) => MOMENTS[k].text)
  return (
    <div className="pt-4 md:hidden">
      <motion.div className="text-[13px] text-ink-3">{date}</motion.div>
      <motion.h3 className="serif mt-1 text-[24px] leading-tight">{title}</motion.h3>
      <motion.p className="mt-1.5 text-[15px] leading-[1.55] text-ink-2">{text}</motion.p>
    </div>
  )
}

function Timeline({ p }: { p: MotionValue<number> }) {
  const progress = useTransform(p, [0, 1], ['4%', '100%'])
  const bg = useTransform(p, [0, 1], ['50% 30%', '50% 70%'])
  return (
    <div className="wrap flex h-full flex-col pt-22 pb-8 sm:pt-24">
      <motion.div style={{ backgroundImage: `url(${wall})`, backgroundPosition: bg }} className="relative min-h-0 flex-1 overflow-hidden rounded-[22px] bg-cover">
        <Stage i={0} p={p}>
          <WhatsAppMessage />
        </Stage>
        <Stage i={1} p={p}>
          <Clearance p={p} />
        </Stage>
        <Stage i={2} p={p}>
          <Answer />
        </Stage>
      </motion.div>
      <div className="relative mt-6 h-px bg-line">
        <motion.div style={{ width: progress }} className="absolute inset-y-0 left-0 bg-ink" />
      </div>
      <div className="flex gap-8 max-md:hidden">
        {MOMENTS.map((m, i) => (
          <Stop key={m.title} i={i} p={p} />
        ))}
      </div>
      <MobileStop p={p} />
    </div>
  )
}

export function HowItWorks() {
  return (
    <div id="how" className="section">
      <div data-snap="start" className="wrap pb-10 text-center sm:pb-16">
        <Reveal>
          <h2 className="serif h-hook">For the people who stay.</h2>
        </Reveal>
      </div>
      <Scene beats={3}>{(p) => <Timeline p={p} />}</Scene>
    </div>
  )
}
