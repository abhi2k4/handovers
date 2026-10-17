import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion'
import { useRef, type ReactNode } from 'react'

/** Fades a block up once, the only motion most of the page uses. */
export function Reveal({ children, className = '', delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-12%' }}
      transition={{ delay, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/** An art-directed backdrop (photo or texture) that the product sits on; the photo drifts slower than the page. */
export function Plate({
  src,
  position = 'center',
  eager = false,
  className = '',
  snap = true,
  children,
}: {
  snap?: boolean
  src: string
  position?: string
  eager?: boolean
  className?: string
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  const still = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], still ? ['0%', '0%'] : ['-7%', '7%'])
  return (
    <div ref={ref} data-snap={snap ? 'center' : undefined} className={className}>
      <Reveal className="plate relative size-full overflow-hidden rounded-[22px]">
        <motion.img
          src={src}
          alt=""
          loading={eager ? 'eager' : 'lazy'}
          fetchPriority={eager ? 'high' : 'auto'}
          className="absolute inset-x-0 -top-[8%] h-[116%] w-full object-cover"
          style={{ objectPosition: position, y }}
        />
        {children}
      </Reveal>
    </div>
  )
}

/** A real capture of the app, floating on a plate. */
export function Shot({ src, alt, className = '' }: { src: string; alt: string; className?: string }) {
  return <img src={src} alt={alt} loading="lazy" className={`shot absolute ${className}`} />
}
