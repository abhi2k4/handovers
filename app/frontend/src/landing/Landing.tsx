import Lenis from 'lenis'
import Snap from 'lenis/snap'
import { useEffect } from 'react'
import { Nav } from './components/Nav'
import './landing.css'
import { Hero } from './sections/Hero'
import { HowItWorks } from './sections/HowItWorks'
import { Memory } from './sections/Memory'
import { Outro } from './sections/Outro'
import { Problem } from './sections/Problem'
import { Product } from './sections/Product'

/** The landing page, at /. The app lives under /dashboard. */
export default function Landing() {
  useEffect(() => {
    document.title = "Handovers: people leave, their context shouldn't"
    const lenis = new Lenis({ lerp: 0.12 })
    // A short wheel or trackpad flick glides to the next section or photo; touch scrolls natively.
    let snap: Snap | undefined
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      snap = new Snap(lenis, {
        type: 'lock',
        distanceThreshold: '100%',
        debounce: 160,
        duration: 1.1,
        easing: (t) => 1 - Math.pow(1 - t, 4),
      })
      const opts = { ignoreTransform: true }
      snap.addElements([...document.querySelectorAll<HTMLElement>('[data-snap="start"]')], { ...opts, align: 'start' })
      snap.addElements([...document.querySelectorAll<HTMLElement>('[data-snap="center"]')], { ...opts, align: 'center' })
    }
    let raf = 0
    const loop = (t: number) => {
      lenis.raf(t)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      snap?.destroy()
      lenis.destroy()
    }
  }, [])

  return (
    <div className="landing">
      <Nav />
      <main>
        <Hero />
        <Problem />
        <Product />
        <HowItWorks />
        <Memory />
      </main>
      <Outro />
    </div>
  )
}
