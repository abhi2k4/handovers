import { useMotionValueEvent, useScroll } from 'framer-motion'
import { useState } from 'react'
import logo from '../logo-nav.png'

const DEMO = '/dashboard'

/** Full-width bar at the top; once you scroll it lifts into a floating liquid-glass capsule. */
export function Nav() {
  const { scrollY } = useScroll()
  const [floating, setFloating] = useState(false)
  useMotionValueEvent(scrollY, 'change', (y) => setFloating(y > 40))

  return (
    <div
      className={`fixed inset-x-0 z-50 flex justify-center px-3 transition-[top] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
        floating ? 'top-3' : 'top-0'
      }`}
    >
      <nav
        className={`flex w-full items-center gap-7 transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          floating ? 'glass h-[54px] max-w-[860px] rounded-full pr-2 pl-5' : 'h-[72px] max-w-[1280px] border border-transparent px-2 sm:px-10'
        }`}
      >
        <a href="/" className="flex items-center gap-2">
          <img src={logo} alt="" className="h-5 w-auto" />
          <span className="text-[15.5px] font-semibold tracking-[-0.01em]">Handovers</span>
        </a>
        <div className="ml-2 hidden items-center gap-6 text-[14px] font-medium text-ink-2 sm:flex">
          <a href="#product" className="transition-colors hover:text-ink">
            Product
          </a>
          <a href="#problem" className="transition-colors hover:text-ink">
            Why
          </a>
          <a href="#how" className="transition-colors hover:text-ink">
            How it works
          </a>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <a href={DEMO} className="btn btn-green !h-9 !px-4 text-[13.5px] whitespace-nowrap">
            Try Handovers
          </a>
        </div>
      </nav>
    </div>
  )
}
