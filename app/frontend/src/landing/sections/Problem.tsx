import { motion, useTransform, type MotionValue } from 'framer-motion'
import { Scene } from '../components/Scene'
import { FRAGMENTS } from '../story'

const DAYS = 22
// Fragments go in this order, spread across the notice period (indices into FRAGMENTS).
const ORDER = [9, 3, 6, 11, 2, 8, 10, 7, 5, 1, 4, 0]

/** One thing only Nisha knows; it blurs away when its day comes. */
function Fragment({ f, at, p }: { f: (typeof FRAGMENTS)[number]; at: number; p: MotionValue<number> }) {
  const opacity = useTransform(p, [at, at + 0.07], [1, 0])
  const blur = useTransform(p, [at, at + 0.07], ['blur(0px)', 'blur(10px)'])
  const y = useTransform(p, [at, at + 0.07], [0, -28])
  return (
    <motion.span
      style={{ left: `${f.x}%`, top: `${f.y}%`, opacity, filter: blur, y }}
      className={`absolute max-w-[42vw] text-[13px] leading-snug text-ink-2 sm:max-w-[19rem] sm:text-[16px] ${f.wide ? 'max-md:hidden' : ''}`}
    >
      {f.text}
    </motion.span>
  )
}

/** A notice period in one screen: the countdown runs and what only she knew drifts away. */
export function Problem() {
  return (
    <Scene id="problem" beats={3} className="mt-24 sm:mt-32">
      {(p) => <Vanish p={p} />}
    </Scene>
  )
}

function Vanish({ p }: { p: MotionValue<number> }) {
  const days = useTransform(p, [0.08, 0.86], [DAYS, 0], { clamp: true })
  const label = useTransform(days, (d) => {
    const n = Math.round(d)
    return n === 0 ? 'Last day' : `${n} ${n === 1 ? 'day' : 'days'} left`
  })
  const bar = useTransform(days, [DAYS, 0], ['0%', '100%'])
  const after = useTransform(p, [0.84, 0.96], [0, 1])
  const afterY = useTransform(p, [0.84, 0.96], [16, 0])

  return (
    <div className="relative mx-auto size-full max-w-[1280px]">
      {FRAGMENTS.map((f, i) => (
        <Fragment key={f.text} f={f} p={p} at={0.12 + (ORDER.indexOf(i) / FRAGMENTS.length) * 0.7} />
      ))}

      <div className="absolute inset-0 flex flex-col items-center justify-center px-5 text-center">
        <div className="flex items-center gap-3 text-[14px] text-ink-2">
          <span className="font-medium text-ink">Nisha Verma</span>
          <span className="relative h-[3px] w-24 overflow-hidden rounded-full bg-line">
            <motion.span style={{ width: bar }} className="absolute inset-y-0 left-0 rounded-full bg-[#c2410c]" />
          </span>
          <motion.span className="w-[6.5rem] text-left tabular-nums">{label}</motion.span>
        </div>
        <h2 className="serif h-section mx-auto mt-7 max-w-[16ch]">When someone leaves, their work leaves with them.</h2>
        <motion.p style={{ opacity: after, y: afterY }} className="mt-7 max-w-[30rem] text-[18px] leading-[1.6] text-ink-2">
          Admin access only she had. Reasons nobody wrote down. Most of it is gone by the last day.
        </motion.p>
      </div>
    </div>
  )
}
