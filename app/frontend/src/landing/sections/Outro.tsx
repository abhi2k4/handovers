import { motion } from 'framer-motion'
import logo from '../logo-nav.png'
import { Reveal } from '../components/Plate'
import { FRAGMENTS } from '../story'

const DEMO = '/dashboard'

export function Outro() {
  return (
    <footer data-snap="start">
      <div className="wrap relative py-32 text-center sm:py-44">
        {/* What drifted away during the notice period comes back, kept. */}
        <div aria-hidden className="pointer-events-none absolute inset-0">
          {FRAGMENTS.filter((f) => f.y < 22 || f.y > 76).map((f, i) => (
            <motion.span
              key={f.text}
              initial={{ opacity: 0, filter: 'blur(10px)', y: -20 }}
              whileInView={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
              viewport={{ once: true, margin: '-20%' }}
              transition={{ delay: 0.2 + i * 0.09, duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
              style={{ left: `${f.x}%`, top: `${f.y}%` }}
              className="absolute max-w-[19rem] text-left text-[14px] leading-snug text-ink-3 max-md:hidden"
            >
              {f.text}
            </motion.span>
          ))}
        </div>
        <Reveal className="relative">
          <h2 className="serif h-hook">
            Give your company
            <br className="max-sm:hidden" /> a brain.
          </h2>
          <p className="mx-auto mt-6 max-w-[30rem] text-[18px] leading-[1.6] text-ink-2">
            The graph finds what matters, people confirm it, and nothing walks out the door.
          </p>
          <a href={DEMO} className="btn btn-green btn-lg mt-10">
            Try the live demo
          </a>
        </Reveal>
      </div>

      <div className="wrap pb-10">
        <div className="flex flex-col gap-6 border-t border-line pt-8 sm:flex-row sm:items-center sm:justify-between">
          <a href="#top" className="flex items-center gap-2">
            <img src={logo} alt="" className="h-5 w-auto" />
            <span className="text-[15px] font-semibold">Handovers</span>
            <span className="text-[13px] text-ink-3">· Built on FalkorDB</span>
          </a>
          <nav className="flex gap-6 text-[14px] text-ink-2">
            <a href="#product" className="hover:text-ink">
              Product
            </a>
            <a href="#how" className="hover:text-ink">
              How it works
            </a>
            <a href={DEMO} className="hover:text-ink">
              Live demo
            </a>
          </nav>
        </div>
      </div>
    </footer>
  )
}
