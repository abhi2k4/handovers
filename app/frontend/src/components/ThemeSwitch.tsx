import { useEffect, useRef, useState } from 'react'
import { Check, Desktop, Moon, Sun } from './icons'
import { setChoice, useTheme, type ThemeChoice } from '../lib/theme'

const OPTIONS: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'Match system', icon: Desktop },
]

/** Light, dark or the operating system's setting, for the whole app (kept in this browser). */
export function ThemeSwitch() {
  const { choice, theme } = useTheme()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const Icon = theme === 'dark' ? Moon : Sun

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => root.current && !root.current.contains(e.target as Node) && setOpen(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={root} className="relative shrink-0">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={`Theme: ${theme}`}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Theme"
        className="flex size-10 items-center justify-center rounded-[4px] bg-page text-ink-2 shadow-[inset_0_0_0_1px_var(--color-control)] transition-colors hover:bg-hover hover:text-ink"
      >
        <Icon size={16} />
      </button>
      {open && (
        <div role="menu" className="absolute top-[calc(100%+6px)] right-0 z-50 w-44 rounded-[6px] bg-page p-1 shadow-raised [animation:pop-in_120ms_ease-out]">
          <div className="eyebrow px-2 pt-1 pb-1.5">Theme</div>
          {OPTIONS.map((o) => (
            <button
              key={o.value}
              role="menuitemradio"
              aria-checked={choice === o.value}
              onClick={() => {
                setChoice(o.value)
                setOpen(false)
              }}
              className="flex w-full items-center gap-2.5 rounded-[4px] px-2 py-1.5 text-left text-[13px] text-ink-2 hover:bg-hover hover:text-ink"
            >
              <o.icon size={15} className="text-ink-3" />
              <span className="flex-1">{o.label}</span>
              {choice === o.value && <Check size={13} weight="bold" className="text-accent" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
