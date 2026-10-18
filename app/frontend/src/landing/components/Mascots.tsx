import {
  AnimatePresence,
  animate,
  motion,
  useAnimationFrame,
  useMotionValue,
  useMotionValueEvent,
  useScroll,
  useTransform,
  useVelocity,
  type MotionValue,
} from 'framer-motion'
import { useEffect, useRef, useState } from 'react'

/**
 * The two people from the logo, walking the story down the page.
 * Blue is leaving and holds what they know; green takes it over. Scroll drives where they stand,
 * the paper flies from one to the other in "How it works", and they meet in the logo pose at the end.
 * While the reader stops to read, they sink until only their heads peek over the edge.
 */

type Who = 'blue' | 'green'

// One entry per stop: hero, problem, product, how, handed over, memory, footer.
const LINES: Partial<Record<Who, string>>[] = [
  { blue: 'Psst. I’m resigning.', green: 'Wait. Who knows what you know?' },
  { blue: 'It’s all in my head… and Slack, and Jira.' },
  { green: 'Whoa. The handover wrote itself?' },
  { blue: 'Here. Everything, with sources.' },
  { green: 'Got it. Your manager approved.' },
  { green: 'And I only see what was handed to me.' },
  {},
]
const QUIPS: Record<Who, string[]> = {
  blue: ['I left very good notes.', 'Ask my successor!', 'Nothing’s lost, promise.', 'Two weeks’ notice, zero panic.'],
  green: ['I inherited a brain.', 'Ask me anything. I’ll cite it.', 'Day one, already ramped.', 'Private notes? Never saw them.'],
}
const WAVE = [true, false, false, false, false, true, false]
const ARM: Record<Who, number[]> = {
  blue: [-14, 22, 6, -8, -2, -38, -10],
  green: [6, 14, -26, -18, -12, 2, -10],
}
const PALETTE: Record<Who, [string, string]> = { blue: ['#1d6ff2', '#8cc0ff'], green: ['#2fae92', '#a9e8cf'] }
const BOTTOM = 10

interface Layout {
  W: number
  S: number
  stops: number[]
}

function measure(): Layout | null {
  const ids = ['top', 'problem', 'product', 'how', 'memory']
  const els = [...ids.map((id) => document.getElementById(id)), document.querySelector<HTMLElement>('.landing > footer')]
  if (els.some((e) => !e)) return null
  const W = window.innerWidth
  const H = window.innerHeight
  const top = (e: HTMLElement) => e.getBoundingClientRect().top + window.scrollY
  const t = (els as HTMLElement[]).map(top)
  // The handover finishes before the film.
  const film = document.getElementById('film')
  const howEnd = film ? top(film) : t[4]
  const max = document.documentElement.scrollHeight - H
  const stops = [0, t[1] - H * 0.5, t[2] - H * 0.5, t[3] - H * 0.3, t[3] + (howEnd - t[3]) * 0.45, t[4] - H * 0.5, max - 4]
  for (let i = 1; i < stops.length; i++) stops[i] = Math.max(stops[i], stops[i - 1] + 1)
  return { W, S: W < 640 ? 58 : W < 1024 ? 84 : 104, stops }
}

export function Mascots() {
  const [layout, setLayout] = useState<Layout | null>(null)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const update = () => setLayout(measure())
    update()
    // Scenes size themselves after fonts and images load.
    const late = setTimeout(update, 1200)
    window.addEventListener('resize', update)
    window.addEventListener('load', update)
    return () => {
      clearTimeout(late)
      window.removeEventListener('resize', update)
      window.removeEventListener('load', update)
    }
  }, [])
  return layout ? <Stage key={`${layout.W}-${layout.stops.join()}`} {...layout} /> : null
}

function Stage({ W, S, stops }: Layout) {
  const H = (S * 4) / 3
  const { scrollY } = useScroll()
  const [stop, setStop] = useState(0)
  const stopRef = useRef(0)
  useMotionValueEvent(scrollY, 'change', (y) => {
    let i = 0
    while (i < stops.length - 1 && y >= stops[i + 1] - 2) i++
    stopRef.current = i
    setStop(i)
  })

  const bx = useTransform(scrollY, stops, [0.04 * W, 0.012 * W, 0.03 * W, W / 2 - S - 80, W / 2 - S - 56, -1.8 * S, W / 2 - S - S * 0.2])
  const gx = useTransform(scrollY, stops, [0.96 * W - S, 0.968 * W - S, 0.955 * W - S, W / 2 + 80, W / 2 + 56, 0.93 * W - S, W / 2 + S * 0.2])
  const pass = useTransform(scrollY, stops, [0, 0, 0, 0, 1, 1, 0.5])
  const arc = useTransform(scrollY, [stops[3], stops[4]], [0, 1], { clamp: true })
  const docScale = useTransform(scrollY, stops, [1, 0.9, 1.35, 1.1, 1.1, 1.15, 1.25])
  const handY = H * 0.36

  // The paper rides in blue's hand, arcs across during the handover, and rests between them at the end.
  const docX = useTransform([bx, gx, pass], ([b, g, p]: number[]) => {
    const from = b + S * 0.98
    const to = g + S * 0.02
    return from + (to - from) * p - S * 0.21
  })
  const docSink = useMotionValue(0)
  const docY = useTransform([arc, docSink], ([a, k]: number[]) => -(handY - S * 0.06) - Math.sin(Math.PI * a) * H * 1.15 + k)
  const docRotate = useTransform(arc, (a) => (a > 0 && a < 1 ? a * 360 : 0) - 8)

  // Bob while the page moves; jump on click.
  const velocity = useVelocity(scrollY)
  const bob = { blue: useMotionValue(0), green: useMotionValue(0) }
  const tilt = { blue: useMotionValue(0), green: useMotionValue(0) }
  const jump = { blue: useMotionValue(0), green: useMotionValue(0) }
  const arm = { blue: useMotionValue(0), green: useMotionValue(0) }
  const sink = useRef({ blue: 0, green: 0 })
  const active = useRef(0)
  const [awake, setAwake] = useState(true)
  const watching = useRef(false)
  useEffect(() => {
    const onVideo = (e: Event) => (watching.current = (e as CustomEvent<boolean>).detail)
    window.addEventListener('handovers:video', onVideo)
    return () => window.removeEventListener('handovers:video', onVideo)
  }, [])
  useAnimationFrame((t) => {
    const raw = Math.abs(velocity.get())
    const v = Math.min(raw / 1400, 1)
    if (raw > 30) active.current = t
    // The intro and the finale stay up; everywhere else they duck while the reader reads.
    const s0 = stopRef.current
    // While the demo video plays they leave the screen entirely, until the reader scrolls on.
    if (watching.current && s0 >= 5) watching.current = false
    const away = watching.current
    const resting = away || (s0 !== 0 && s0 !== 6 && t - active.current > 2600)
    if (resting === awake) setAwake(!resting)
    for (const who of ['blue', 'green'] as Who[]) {
      const ph = who === 'blue' ? 0 : 1.7
      const k = sink.current
      k[who] += ((away ? H * 1.3 : resting ? H * 0.6 : 0) - k[who]) * 0.07
      bob[who].set(-Math.abs(Math.sin(t / 110 + ph)) * 9 * v + jump[who].get() + k[who])
      tilt[who].set(Math.sin(t / 220 + ph) * 5 * v)
      const s = stopRef.current
      const wave = WAVE[s] && who === 'blue' ? Math.sin(t / 150) * 20 : 0
      arm[who].set(ARM[who][s] + wave + Math.sin(t / 900 + ph) * 2)
    }
    const p = pass.get()
    docSink.set(sink.current.blue * (1 - p) + sink.current.green * p)
  })

  const [quip, setQuip] = useState<{ who: Who; text: string; n: number } | null>(null)
  const quipTimer = useRef<ReturnType<typeof setTimeout>>(undefined)
  const poke = (who: Who) => {
    active.current = performance.now()
    animate(jump[who], [0, -S * 0.7, 0], { duration: 0.55, ease: [0.33, 1, 0.68, 1], times: [0, 0.42, 1] })
    const list = QUIPS[who]
    setQuip((q) => ({ who, text: list[Math.floor(Math.random() * list.length)], n: (q?.n ?? 0) + 1 }))
    clearTimeout(quipTimer.current)
    quipTimer.current = setTimeout(() => setQuip(null), 2400)
  }

  const line = (who: Who) => (quip?.who === who ? quip.text : awake ? LINES[stop][who] : undefined)
  const small = W < 640

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-40 overflow-hidden">
      <Person who="blue" x={bx} S={S} bob={bob.blue} tilt={tilt.blue} arm={arm.blue} onPoke={() => poke('blue')} />
      <Person who="green" x={gx} S={S} bob={bob.green} tilt={tilt.green} arm={arm.green} onPoke={() => poke('green')} />

      <motion.div className="absolute" style={{ left: docX, bottom: BOTTOM, y: docY, rotate: docRotate, scale: docScale, width: S * 0.42 }}>
        <Paper glow={stop >= 5} />
      </motion.div>

      {!small && (
        <>
          <Bubble text={line('blue')} id={`b${stop}-${quip?.who === 'blue' ? quip.n : ''}`} x={bx} side="left" S={S} W={W} H={H} />
          <Bubble text={line('green')} id={`g${stop}-${quip?.who === 'green' ? quip.n : ''}`} x={gx} side="right" S={S} W={W} H={H} />
        </>
      )}

      <AnimatePresence>{stop === 6 && <Confetti key="confetti" S={S} />}</AnimatePresence>
    </div>
  )
}

function Person({ who, x, S, bob, tilt, arm, onPoke }: { who: Who; x: MotionValue<number>; S: number; bob: MotionValue<number>; tilt: MotionValue<number>; arm: MotionValue<number>; onPoke: () => void }) {
  const svg = useRef<SVGSVGElement>(null)
  const armRef = useRef<SVGGElement>(null)
  const pupils = useRef<SVGGElement>(null)
  const flip = who === 'green'

  useMotionValueEvent(arm, 'change', (a) => armRef.current?.setAttribute('transform', `rotate(${a} 70 84)`))
  // The eyes follow the pointer.
  useEffect(() => {
    const move = (e: PointerEvent) => {
      const r = svg.current?.getBoundingClientRect()
      if (!r || !pupils.current) return
      let dx = e.clientX - (r.left + r.width / 2)
      const dy = e.clientY - (r.top + r.height * 0.2)
      if (flip) dx = -dx
      const d = Math.hypot(dx, dy) || 1
      const k = Math.min(d / 120, 1) * 2.3
      pupils.current.setAttribute('transform', `translate(${((dx / d) * k).toFixed(2)} ${((dy / d) * k).toFixed(2)})`)
    }
    window.addEventListener('pointermove', move)
    return () => window.removeEventListener('pointermove', move)
  }, [flip])

  const [c1, c2] = PALETTE[who]
  return (
    <motion.button
      type="button"
      tabIndex={-1}
      onClick={onPoke}
      className="pointer-events-auto absolute cursor-pointer"
      style={{ left: x, bottom: BOTTOM, y: bob, rotate: tilt, width: S, originY: 1 }}
      whileHover={{ scale: 1.06 }}
      whileTap={{ scaleY: 0.9, scaleX: 1.08 }}
    >
      <svg ref={svg} viewBox="0 0 124 160" className="block w-full overflow-visible" style={{ transform: flip ? 'scaleX(-1)' : undefined }}>
        <defs>
          <linearGradient id={`m-${who}`} x1="0" y1="0" x2="0.6" y2="1">
            <stop offset="0" stopColor={c1} />
            <stop offset="1" stopColor={c2} />
          </linearGradient>
          <linearGradient id={`m-${who}-head`} x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor={c1} />
            <stop offset="1" stopColor={c2} />
          </linearGradient>
        </defs>
        <ellipse cx="60" cy="157" rx="34" ry="4" fill="rgba(22,24,29,0.12)" />
        <path d="M30 148V96c0-19 13.4-32 30-32s30 13 30 32v52a8 8 0 0 1-8 8H38a8 8 0 0 1-8-8Z" fill={`url(#m-${who})`} />
        <g ref={armRef} transform="rotate(0 70 84)">
          <path d="M66 89c14-2 22 6 30 13 7 6 13 8 22 8" fill="none" stroke="rgba(22,24,29,0.12)" strokeWidth="17" strokeLinecap="round" />
          <path d="M66 86c14-2 22 6 30 13 7 6 13 8 22 8" fill="none" stroke={`url(#m-${who})`} strokeWidth="17" strokeLinecap="round" />
        </g>
        <circle cx="60" cy="33" r="27" fill={`url(#m-${who}-head)`} />
        <g className="mascot-blink" style={{ transformOrigin: '60px 31px', animationDelay: flip ? '1.3s' : '0s' }}>
          <ellipse cx="52" cy="31" rx="5.2" ry="6" fill="#fff" />
          <ellipse cx="70" cy="31" rx="5.2" ry="6" fill="#fff" />
          <g ref={pupils}>
            <circle cx="53" cy="32" r="2.7" fill="#16181d" />
            <circle cx="71" cy="32" r="2.7" fill="#16181d" />
          </g>
        </g>
        <path d="M54 44c3.5 3 8.5 3 12 0" fill="none" stroke="#16181d" strokeOpacity="0.55" strokeWidth="2.2" strokeLinecap="round" />
        <circle cx="45" cy="41" r="3.4" fill="#ff7aa8" opacity="0.35" />
        <circle cx="76" cy="41" r="3.4" fill="#ff7aa8" opacity="0.35" />
      </svg>
    </motion.button>
  )
}

function Paper({ glow }: { glow: boolean }) {
  return (
    <svg viewBox="0 0 44 54" className="block w-full overflow-visible">
      {glow && <rect x="-6" y="-6" width="56" height="66" rx="12" fill="#8cc0ff" opacity="0.35" style={{ filter: 'blur(8px)' }} />}
      <path d="M6 1h24l13 13v33a6 6 0 0 1-6 6H6a6 6 0 0 1-6-6V7a6 6 0 0 1 6-6Z" fill="#f4f8ff" stroke="#c9dcf8" />
      <path d="M30 1v9a4 4 0 0 0 4 4h9" fill="#dce9fb" stroke="#c9dcf8" />
      <rect x="8" y="20" width="22" height="3.2" rx="1.6" fill="#9ec3f5" />
      <rect x="8" y="28" width="27" height="3.2" rx="1.6" fill="#9ec3f5" />
      <rect x="8" y="36" width="17" height="3.2" rx="1.6" fill="#9ec3f5" />
    </svg>
  )
}

function Bubble({ text, id, x, side, S, W, H }: { text?: string; id: string; x: MotionValue<number>; side: 'left' | 'right'; S: number; W: number; H: number }) {
  const left = useTransform(x, (v) => v + S * 0.25)
  const right = useTransform(x, (v) => W - v - S * 0.75)
  return (
    <AnimatePresence mode="wait">
      {text && (
        <motion.div
          key={id}
          initial={{ opacity: 0, y: 10, scale: 0.85 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.92, transition: { duration: 0.15 } }}
          transition={{ type: 'spring', stiffness: 420, damping: 26 }}
          className="absolute max-w-[17rem] rounded-2xl bg-white px-3.5 py-2 text-[13.5px] leading-snug font-medium text-ink shadow-shot"
          style={{ bottom: BOTTOM + H + 14, ...(side === 'left' ? { left, originX: 0 } : { right, originX: 1 }), originY: 1 }}
        >
          {text}
          <span className={`absolute -bottom-1.5 size-3 rotate-45 bg-white ${side === 'left' ? 'left-5' : 'right-5'}`} />
        </motion.div>
      )}
    </AnimatePresence>
  )
}

const BITS = Array.from({ length: 22 }, (_, i) => {
  const a = (i / 22) * Math.PI * 2 + (i % 3) * 0.3
  return { a, d: 90 + (i % 5) * 34, c: ['#1d6ff2', '#2fae92', '#8cc0ff', '#a9e8cf', '#ffb84d'][i % 5], r: i % 2 ? 45 : -60, s: 6 + (i % 3) * 3 }
})

function Confetti({ S }: { S: number }) {
  return (
    <div className="absolute left-1/2" style={{ bottom: BOTTOM + S * 0.9 }}>
      {BITS.map((b, i) => (
        <motion.span
          key={i}
          className="absolute block rounded-[2px]"
          style={{ width: b.s, height: b.s * 0.6, background: b.c }}
          initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
          animate={{ x: Math.cos(b.a) * b.d, y: [0, -Math.abs(Math.sin(b.a)) * b.d - 40, 60], opacity: [1, 1, 0], rotate: b.r * 6 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.6, ease: 'easeOut', times: [0, 0.45, 1] }}
        />
      ))}
    </div>
  )
}
