import { useScroll, type MotionValue } from 'framer-motion'
import { useRef, type ReactNode } from 'react'

/**
 * A pinned, scroll-driven scene: the section is `beats` screens tall and its frame stays put while
 * `progress` runs 0 -> 1. One snap point per beat, so a wheel flick advances the story one step.
 */
export function Scene({
  id,
  beats,
  className = '',
  children,
}: {
  id?: string
  beats: number
  className?: string
  children: (progress: MotionValue<number>) => ReactNode
}) {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  return (
    <section ref={ref} id={id} className={`relative ${className}`} style={{ height: `${beats * 100}svh` }}>
      {Array.from({ length: beats }, (_, i) => (
        <div key={i} data-snap="start" aria-hidden className="absolute inset-x-0 h-0" style={{ top: `${i * 100}svh` }} />
      ))}
      <div className="sticky top-0 h-svh overflow-hidden">{children(scrollYProgress)}</div>
    </section>
  )
}

