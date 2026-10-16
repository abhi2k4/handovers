import { useSyncExternalStore } from 'react'

/**
 * Light or dark for the app (never the landing page). The choice is kept in this browser;
 * "system" follows the operating system and changes with it. The `dark` class on <html> switches
 * every colour token (styles/index.css), so components only use tokens.
 */
export type ThemeChoice = 'system' | 'light' | 'dark'

const KEY = 'handovers.theme'
const media = typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)') : null
const listeners = new Set<() => void>()

export function getChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'light' || v === 'dark' ? v : 'system'
  } catch {
    return 'system'
  }
}

export function resolved(choice: ThemeChoice = getChoice()): 'light' | 'dark' {
  return choice === 'system' ? (media?.matches ? 'dark' : 'light') : choice
}

/** Put the class on <html>. Called before the app renders (no flash) and on every change. */
export function applyTheme(): void {
  const dark = resolved() === 'dark'
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
}

/** Leaving the app (e.g. a link to the landing page): back to the landing page's own look. */
export function clearTheme(): void {
  document.documentElement.classList.remove('dark')
  document.documentElement.style.colorScheme = ''
}

export function setChoice(choice: ThemeChoice): void {
  try {
    if (choice === 'system') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, choice)
  } catch {
    // storage unavailable: the choice lasts for this page only
  }
  applyTheme()
  listeners.forEach((l) => l())
}

media?.addEventListener('change', () => {
  if (getChoice() === 'system') {
    applyTheme()
    listeners.forEach((l) => l())
  }
})

function subscribe(l: () => void) {
  listeners.add(l)
  return () => listeners.delete(l)
}

/** The current choice and what it resolves to; re-renders when either changes. */
export function useTheme(): { choice: ThemeChoice; theme: 'light' | 'dark' } {
  const choice = useSyncExternalStore(subscribe, getChoice, () => 'system' as ThemeChoice)
  const theme = useSyncExternalStore(subscribe, () => resolved(), () => 'light' as const)
  return { choice, theme }
}

/** Colours for the canvas-drawn graphs (Cytoscape cannot read CSS variables). */
export function graphInk(theme: 'light' | 'dark') {
  return theme === 'dark'
    ? { text: '#c9d2de', edge: '#2e3846', surface: '#10151c', root: '#e8edf4', accent: '#77abff', ring: '#1e3a66' }
    : { text: '#3b3a36', edge: '#e2e1de', surface: '#ffffff', root: '#21201c', accent: '#0071e3', ring: '#bfdbfe' }
}
