import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import poster from '../art/film-loop.webp'
import loopWebm from '../art/film-loop.webm'

/** The promo film on YouTube. */
export const FILM_ID = 'srSwznTROa0'

const ease = [0.22, 1, 0.36, 1] as const

/**
 * The 60-second film, on a dark stage where the company brain from the film turns silently.
 * YouTube loads only when someone presses play; the player then takes over the stage, with sound.
 */
export function Film() {
  const stage = useRef<HTMLDivElement>(null)
  const loop = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)

  // The silent loop runs only while the stage is on screen and the film isn't playing.
  useEffect(() => {
    const v = loop.current
    if (!v || !stage.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !playing) void v.play().catch(() => {})
      else v.pause()
    })
    io.observe(stage.current)
    return () => io.disconnect()
  }, [playing])

  const play = (on: boolean) => {
    setPlaying(on)
    // The mascots step aside while the film plays, so they never sit on the player.
    window.dispatchEvent(new CustomEvent('handovers:video', { detail: on }))
  }

  return (
    <section id="film" data-snap="start" className="mt-28 bg-[#050507] text-white sm:mt-40">
      <div ref={stage} className="relative isolate flex h-svh min-h-[560px] items-center justify-center overflow-hidden">
        <motion.video
          ref={loop}
          muted
          loop
          playsInline
          preload="metadata"
          poster={poster}
          aria-hidden
          animate={{ opacity: playing ? 0.18 : 1, scale: playing ? 1.08 : 1 }}
          transition={{ duration: 1.2, ease }}
          className="absolute inset-0 -z-10 size-full object-cover"
        >
          <source src={loopWebm} type="video/webm" />
        </motion.video>
        {/* Edges melt into the page so the stage reads as depth, not a box; this also hides the clip's captions. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_50%_42%,transparent_30%,#050507_78%)]" />
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-40 bg-gradient-to-b from-[#050507] to-transparent" />
        <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-[34%] bg-gradient-to-t from-[#050507] from-45% to-transparent" />

        <AnimatePresence mode="wait" initial={false}>
          {playing ? (
            <motion.div
              key="player"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.6, ease }}
              className="relative w-[min(92vw,1180px,calc((100svh-160px)*16/9))]"
            >
              <div className="aspect-video overflow-hidden rounded-[14px] bg-black shadow-[0_40px_120px_-20px_rgba(0,0,0,0.9),0_0_0_1px_rgba(255,255,255,0.08)] sm:rounded-[20px]">
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${FILM_ID}?autoplay=1&rel=0&modestbranding=1&playsinline=1`}
                  title="Handovers: the film"
                  allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                  allowFullScreen
                  className="size-full"
                />
              </div>
              <div className="mt-4 flex items-center justify-between text-[14px] text-white/55">
                <a href={`https://youtu.be/${FILM_ID}`} target="_blank" rel="noreferrer" className="transition-colors hover:text-white">
                  Watch on YouTube ↗
                </a>
                <button type="button" onClick={() => play(false)} className="flex items-center gap-2 font-medium transition-colors hover:text-white">
                  <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden>
                    <path d="M3.5 3.5l9 9m0-9l-9 9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                  Close
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="intro"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10, filter: 'blur(6px)' }}
              transition={{ duration: 0.7, ease }}
              className="wrap relative text-center"
            >
              {/* A soft halo keeps the headline clear of the film's passing source tags. */}
              <div aria-hidden className="pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[150%] w-[min(1100px,120%)] -translate-x-1/2 -translate-y-1/2 bg-[radial-gradient(closest-side,rgba(5,5,7,0.72),rgba(5,5,7,0.35)_60%,transparent)]" />
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-25%' }}
                transition={{ duration: 0.8, ease }}
                className="text-[12.5px] font-semibold tracking-[0.26em] text-white/50 uppercase"
              >
                The film · 60 seconds
              </motion.p>
              <motion.h2
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-25%' }}
                transition={{ delay: 0.1, duration: 1, ease }}
                className="serif h-hook mx-auto mt-6 max-w-[12ch] [text-shadow:0_4px_40px_rgba(5,5,7,0.8)]"
              >
                Every company has a <span className="italic text-[#7ff0b8]">brain.</span>
              </motion.h2>
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-25%' }}
                transition={{ delay: 0.25, duration: 0.9, ease }}
                className="mt-10 flex flex-col items-center gap-4"
              >
                <button
                  type="button"
                  onClick={() => play(true)}
                  className="group flex h-16 items-center gap-4 rounded-full bg-white pr-7 pl-2 text-ink shadow-[0_20px_60px_-10px_rgba(127,240,184,0.35)] transition-transform duration-300 hover:scale-[1.04]"
                >
                  <span className="relative flex size-12 items-center justify-center rounded-full bg-ink text-white">
                    <span className="absolute inset-0 animate-ping rounded-full bg-ink/30 [animation-duration:2.2s]" />
                    <svg viewBox="0 0 24 24" className="relative ml-0.5 size-5" aria-hidden>
                      <path fill="currentColor" d="M7 4.8v14.4a1 1 0 0 0 1.5.86l11.6-7.2a1 1 0 0 0 0-1.72L8.5 3.94A1 1 0 0 0 7 4.8Z" />
                    </svg>
                  </span>
                  <span className="text-[17px] font-semibold">Play the film</span>
                </button>
                <span className="flex items-center gap-2 text-[13px] text-white/45">
                  <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden>
                    <path fill="currentColor" d="M7.2 2.6 4.1 5.2H2.2A.7.7 0 0 0 1.5 6v4c0 .4.3.7.7.7h1.9l3.1 2.7c.4.3 1 0 1-.5V3.1c0-.5-.6-.8-1-.5Z" />
                    <path d="M10.6 5.4a3.6 3.6 0 0 1 0 5.2M12.6 3.6a6.2 6.2 0 0 1 0 8.8" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinecap="round" />
                  </svg>
                  Best with sound on
                </span>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
