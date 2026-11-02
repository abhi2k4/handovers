import '@fontsource-variable/geist-mono'
import { IconContext } from '@phosphor-icons/react/dist/lib/context'
import { useEffect } from 'react'
import { RouterProvider } from 'react-router'
import { prefetchRarePages, router } from './router'

/** The product, under /dashboard. */
export default function App() {
  useEffect(() => {
    document.title = 'Handovers'
    // Once the first screen is up, quietly fetch the on-demand pages.
    const idle = window.requestIdleCallback ?? ((cb: () => void) => window.setTimeout(cb, 1500))
    idle(() => prefetchRarePages())
  }, [])
  return (
    <IconContext.Provider value={{ weight: 'regular', mirrored: false }}>
      <RouterProvider router={router} />
    </IconContext.Provider>
  )
}
