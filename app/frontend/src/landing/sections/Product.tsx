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
    <motion.li style={{ opacity, backgroundColor: bg }} className="rounded-[12px] px-3.5 py-2">
      <div className="flex items-center gap-2 text-[11.5px] text-ink-3">
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
      <motion.p style={s.line ? undefined : { filter: blur }} className="font-system mt-0.5 truncate text-[13px] leading-[1.45] text-ink">
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
  const rule = useTransform(p, [t + 0.01, t + 0.07], ['rgba(22,24,29,0)', 'rgba(22,24,29,0.1)'])
  return (
    <div>
      {head && (
        <motion.div style={{ opacity: headOpacity }} className="pt-3.5 pb-0.5 text-[10.5px] max-sm:hidden font-semibold tracking-[0.07em] text-ink-3 uppercase">
          {s.line!.section}
        </motion.div>
      )}
      <motion.div style={{ borderColor: rule }} className="flex items-baseline gap-4 border-b py-2">
        <motion.p style={{ clipPath: clip }} className="min-w-0 flex-1 text-[14px] leading-snug text-ink">
          {s.line!.text}
        </motion.p>
        <motion.div style={{ opacity: meta }} className="flex shrink-0 items-center gap-1.5 text-[11.5px] text-ink-3 max-sm:hidden">
          <Glyph tool={s.tool} className="size-3" />
          {s.where}
        </motion.div>
      </motion.div>
    </div>
  )
}

function Signature({ role, name, t, p }: { role: string; name: string; t: number; p: MotionValue<number> }) {
  const wipe = useTransform(p, [t, t + 0.06], [100, 0], { clamp: true })
  const clip = useTransform(wipe, (w) => `inset(-8px ${w}% -8px 0)`)
  return (
    <div className="min-w-0 flex-1">
      <motion.div style={{ clipPath: clip }} className="serif h-7 truncate text-[20px] text-green-deep italic sm:text-[22px]">
        <span className="sm:hidden">{name.split(' ')[0]}</span>
        <span className="max-sm:hidden">{name}</span>
      </motion.div>
      <div className="mt-1 border-t border-ink/25 pt-1 text-[11px] text-ink-3">{role}</div>
    </div>
  )
}

function Writing({ p }: { p: MotionValue<number> }) {
  const lined = SIGNALS.map((s, i) => ({ s, t: at(i) })).filter((x) => x.s.line)
  return (
    <div className="wrap flex h-full max-w-[1120px]! flex-col justify-center pt-20 pb-6 lg:flex-row lg:items-center lg:gap-14 lg:pt-14">
      <div className="text-center lg:w-[42%] lg:shrink-0 lg:text-left">
        <h2 className="serif mx-auto max-w-[14ch] text-[clamp(2.25rem,3.6vw,3.4rem)] leading-[1.02] tracking-[-0.03em] lg:mx-0">Handovers that write themselves.</h2>
        <p className="mx-auto mt-4 max-w-[25rem] text-[16px] leading-[1.6] text-ink-2 max-sm:hidden lg:mx-0">
          It reads the work as it happens, in chat, documents, tickets and customer records. When someone resigns, the
          handover document is already written, ready for three signatures. Private notes never cross.
        </p>
        <ul className="mt-6 -ml-3.5 hidden flex-col gap-0.5 lg:flex">
          {SIGNALS.map((s, i) => (
            <Raw key={s.raw} s={s} t={at(i)} p={p} />
          ))}
        </ul>
      </div>

      <div className="mx-auto mt-6 w-full max-w-[34rem] min-w-0 rounded-[18px] bg-white p-5 shadow-shot sm:px-7 sm:py-6 lg:mt-0 lg:flex-1">
        <div className="flex items-baseline justify-between gap-4 border-b border-line pb-3">
          <div>
            <div className="text-[12px] text-ink-3">Handover document</div>
            <div className="serif mt-0.5 text-[24px] leading-tight sm:text-[26px]">Nisha Verma</div>
          </div>
          <div className="text-right text-[12px] leading-[1.5] text-ink-3">
            Last day 3 Nov
            <br />
            To Ananya Pillai
          </div>
        </div>
        <div className="min-h-[230px] sm:min-h-[280px]">
          {lined.map(({ s, t }, i) => (
            <Line key={s.raw} s={s} t={t} p={p} head={i === 0 || lined[i - 1].s.line!.section !== s.line!.section} />
          ))}
        </div>
        <div className="mt-5 flex gap-4 sm:gap-5">
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
