import { motion } from 'framer-motion'
import { GLYPHS } from '../../components/platformGlyphs'
import readiness from '../art/app-readiness.webp'
import desk from '../art/desk-window.webp'
import { Plate, Shot } from '../components/Plate'

const DEMO = '/dashboard'

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { delay, duration: 0.8, ease: [0.22, 1, 0.36, 1] as const },
})

/** A phone notification, the way HR first hears about a resignation. */
function Notification() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.1, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className="font-system absolute inset-x-[6%] bottom-[6%] rounded-[22px] bg-white/80 p-3.5 shadow-shot backdrop-blur-xl sm:inset-x-auto sm:bottom-[9%] sm:left-[5%] sm:w-[min(360px,34%)]"
    >
      <div className="flex gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-[#25d366]">
          <svg viewBox="0 0 24 24" className="size-5 text-white" aria-hidden>
            <path fill="currentColor" d={GLYPHS.whatsapp[1]} />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[14px] font-semibold text-black">Handovers</span>
            <span className="text-[12px] text-black/45">now</span>
          </div>
          <p className="mt-0.5 text-[13.5px] leading-[1.35] text-black/80">
            Nisha Verma resigned. Last day 3 Nov. She is the only admin on 3 accounts.
          </p>
        </div>
      </div>
    </motion.div>
  )
}

export function Hero() {
  return (
    <header id="top" data-snap="start" className="pt-32 sm:pt-44">
      <div className="wrap text-center">
        <motion.p {...rise(0.05)} className="text-[15px] font-medium text-ink-2">
          The company brain for HR
        </motion.p>
        <motion.h1 {...rise(0.12)} className="serif h-hero mt-5">
          People leave.
          <br />
          <span className="lg:whitespace-nowrap">Their context shouldn&rsquo;t.</span>
        </motion.h1>
        <div className="mt-8 flex flex-col items-center gap-9">
          <motion.p {...rise(0.24)} className="max-w-[44rem] text-[19px] leading-[1.55] text-ink-2">
            Handovers learns how your company works, from the tools people already use.
            <br className="max-sm:hidden" /> When someone resigns, everything HR needs is already written.
          </motion.p>
          <motion.div {...rise(0.34)} className="flex items-center justify-center gap-6">
            <a href={DEMO} className="btn btn-green btn-lg">
              See the live demo
            </a>
            <a href="#how" className="text-[15px] font-semibold text-ink underline-offset-4 hover:underline">
              How it works
            </a>
          </motion.div>
        </div>
      </div>

      <div className="wrap mt-14 sm:mt-20">
        <Plate src={desk} eager position="50% 60%" className="aspect-[4/5] sm:aspect-[16/10] lg:aspect-[16/9]">
          <Shot
            src={readiness}
            alt="A live handover in the app: seven checks before the last day, each with an owner"
            className="top-[7%] left-[6%] w-[150%] max-w-none sm:top-[9%] sm:right-[5%] sm:left-auto sm:w-[54%]"
          />
          <Notification />
        </Plate>
      </div>
    </header>
  )
}
