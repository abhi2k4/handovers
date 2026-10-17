import { motion, useTransform, type MotionValue } from 'framer-motion'
import { GLYPHS } from '../../components/platformGlyphs'
import { Scene } from '../components/Scene'
import { SIGNALS, type Signal } from '../story'

/** Scroll progress at which each signal is read; its document line writes just after. */
const at = (i: number) => 0.08 + i * 0.105
const SIGN = [
  { role: 'Prepared by', name: 'Nisha Verma', at: 0.76 },
  { role: 'Reviewed by', name: 'Aditi Menon', at: 0.84 },
  { role: 'Received by', name: 'Ananya Pillai', at: 0.92 },
]

function Glyph({ tool, className = '' }: { tool: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`shrink-0 ${className}`} aria-hidden>
      <path fill="currentColor" d={GLYPHS[tool][1]} />
    </svg>
  )
}

/** A raw message or note as the connector reads it: dim until its turn, then lit. */
function Raw({ s, t, p }: { s: Signal; t: number; p: MotionValue<number> }) {
  const opacity = useTransform(p, [t - 0.05, t, t + 0.08], [0.28, 1, 0.6])
  const bg = useTransform(p, [t - 0.03, t, t + 0.08], ['rgba(255,255,255,0)', 'rgba(255,255,255,1)', 'rgba(255,255,255,0.5)'])
  const color = useTransform(p, [t - 0.03, t], ['#8a8e98', GLYPHS[s.tool][0]])
  const lock = useTransform(p, [t, t + 0.03], [0, 1])
  const blur = useTransform(p, [t, t + 0.04], ['blur(0px)', 'blur(5px)'])
  return (
    <motion.li style={{ opacity, backgroundColor: bg }} className="rounded-[14px] px-4 py-3">
      <div className="flex items-center gap-2 text-[12.5px] text-ink-3">
        <motion.span style={{ color }} className="flex">
          <Glyph tool={s.tool} className="size-3.5" />
        </motion.span>
        {s.where}
        {!s.line && (
          <motion.span style={{ opacity: lock }} className="ml-auto flex items-center gap-1 font-medium text-ink">
            <svg viewBox="0 0 16 16" className="size-3" aria-hidden>
              <path fill="currentColor" d="M4 7V5a4 4 0 1 1 8 0v2h.5A1.5 1.5 0 0 1 14 8.5v5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 13.5v-5A1.5 1.5 0 0 1 3.5 7H4Zm2 0h4V5a2 2 0 1 0-4 0v2Z" />
            </svg>
            Stays private
          </motion.span>
        )}
      </div>
      <motion.p style={s.line ? undefined : { filter: blur }} className="font-system mt-1 text-[14px] leading-[1.45] text-ink">
        {s.raw}
      </motion.p>
    </motion.li>
  )
}

/** A line of the handover, typed out left to right, with the source it came from. */
function Line({ s, t, p, head }: { s: Signal; t: number; p: MotionValue<number>; head: boolean }) {
  const wipe = useTransform(p, [t + 0.01, t + 0.07], [100, 0], { clamp: true })
  const clip = useTransform(wipe, (w) => `inset(-4px ${w}% -4px 0)`)
  const meta = useTransform(p, [t + 0.06, t + 0.09], [0, 1])
  const headOpacity = useTransform(p, [t - 0.01, t + 0.02], [0, 1])
  return (
    <div>
      {head && (
        <motion.div style={{ opacity: headOpacity }} className="pt-5 pb-1 text-[11.5px] max-sm:hidden font-semibold tracking-[0.06em] text-ink-3 uppercase">
          {s.line!.section}
        </motion.div>
      )}
      <div className="border-b border-line py-2 sm:py-2.5">
        <motion.p style={{ clipPath: clip }} className="text-[14.5px] leading-snug text-ink sm:text-[15px]">
          {s.line!.text}
        </motion.p>
        <motion.div style={{ opacity: meta }} className="mt-1 flex max-sm:hidden items-center gap-1.5 text-[12px] text-ink-3">
          <Glyph tool={s.tool} className="size-3" />
          {s.where}
        </motion.div>
      </div>
    </div>
  )
}

function Signature({ role, name, t, p }: { role: string; name: string; t: number; p: MotionValue<number> }) {
  const wipe = useTransform(p, [t, t + 0.06], [100, 0], { clamp: true })
  const clip = useTransform(wipe, (w) => `inset(-8px ${w}% -8px 0)`)
  return (
    <div className="min-w-0 flex-1">
      <motion.div style={{ clipPath: clip }} className="serif h-8 truncate text-[22px] text-green-deep italic sm:text-[26px]">
        <span className="sm:hidden">{name.split(' ')[0]}</span>
        <span className="max-sm:hidden">{name}</span>
      </motion.div>
      <div className="mt-1 border-t border-ink/25 pt-1.5 text-[11.5px] text-ink-3">{role}</div>
    </div>
  )
}

function Writing({ p }: { p: MotionValue<number> }) {
  const lined = SIGNALS.map((s, i) => ({ s, t: at(i) })).filter((x) => x.s.line)
  return (
    <div className="wrap flex h-full flex-col justify-center pt-20 pb-6 lg:flex-row lg:items-center lg:gap-16 lg:pt-16">
      <div className="text-center lg:w-[40%] lg:shrink-0 lg:text-left">
        <h2 className="serif h-section mx-auto max-w-[14ch] lg:mx-0">Handovers that write themselves.</h2>
        <p className="mx-auto mt-5 max-w-[26rem] text-[17px] leading-[1.6] text-ink-2 max-sm:hidden lg:mx-0">
          It reads the work as it happens. When someone resigns, the document is already there.
        </p>
        <ul className="mt-8 -ml-4 hidden flex-col gap-1 lg:flex">
          {SIGNALS.map((s, i) => (
            <Raw key={s.raw} s={s} t={at(i)} p={p} />
          ))}
        </ul>
      </div>

      <div className="mx-auto mt-6 w-full max-w-[34rem] min-w-0 rounded-[18px] bg-white p-5 shadow-shot sm:p-8 lg:mt-0 lg:max-w-none lg:flex-1">
        <div className="flex items-baseline justify-between gap-4 border-b border-line pb-4">
          <div>
            <div className="text-[12px] text-ink-3">Handover document</div>
            <div className="serif mt-0.5 text-[26px] leading-tight sm:text-[30px]">Nisha Verma</div>
          </div>
          <div className="text-right text-[12px] leading-[1.5] text-ink-3">
            Last day 3 Nov
            <br />
            To Ananya Pillai
          </div>
        </div>
        <div className="-mt-1 min-h-[250px] sm:min-h-[340px]">
          {lined.map(({ s, t }, i) => (
            <Line key={s.raw} s={s} t={t} p={p} head={i === 0 || lined[i - 1].s.line!.section !== s.line!.section} />
          ))}
        </div>
        <div className="mt-6 flex gap-4 sm:gap-6">
          {SIGN.map((x) => (
            <Signature key={x.role} role={x.role} name={x.name} t={x.at} p={p} />
          ))}
        </div>
      </div>
    </div>
  )
}

/** Raw work on the left becomes the handover on the right; the private note never crosses. */
export function Product() {
  return <Scene id="product" beats={4}>{(p) => <Writing p={p} />}</Scene>
}
