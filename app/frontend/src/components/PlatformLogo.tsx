/* Platform logos for the Integrations page. Glyphs from Simple Icons (CC0, simpleicons.org),
 * drawn in each brand's own colour; Microsoft and Google use their multi-colour marks. */

import { GLYPHS } from './platformGlyphs'


/** Microsoft's four-square mark (Entra ID and Microsoft sign-in). */
function MicrosoftMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 21 21" aria-hidden>
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  )
}

/** Google's multi-colour "G", as Google's own sign-in buttons show it. */
function GoogleMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  )
}

/** The platform's logo by connector or sign-in provider id; a lettered mark when there is none. */
export function PlatformMark({ id, name, size = 22 }: { id: string; name: string; size?: number }) {
  if (id === 'entra' || id === 'microsoft') return <MicrosoftMark size={size} />
  if (id === 'google' || id === 'google_workspace') return <GoogleMark size={size} />
  const glyph = GLYPHS[id]
  if (glyph)
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
        <path fill={glyph[0]} d={glyph[1]} />
      </svg>
    )
  return (
    <span aria-hidden className="font-semibold text-ink-2" style={{ fontSize: Math.round(size * 0.75) }}>
      {name.charAt(0)}
    </span>
  )
}

/** The logo on a tile, as rows and cards show it. */
export function PlatformLogo({ id, name, muted = false }: { id: string; name: string; muted?: boolean }) {
  return (
    <span
      className={`flex size-10 shrink-0 items-center justify-center rounded-[6px] bg-page shadow-[inset_0_0_0_1px_var(--color-line)] ${muted ? 'opacity-60 grayscale' : ''}`}
    >
      <PlatformMark id={id} name={name} />
    </span>
  )
}
