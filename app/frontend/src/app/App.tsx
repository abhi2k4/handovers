import '@fontsource-variable/geist-mono'
import { IconContext } from '@phosphor-icons/react/dist/lib/context'
import { useEffect } from 'react'
import { RouterProvider } from 'react-router'
import { router } from './router'

/** The product, under /dashboard. */
export default function App() {
  useEffect(() => {
    document.title = 'Handovers'
  }, [])
  return (
    <IconContext.Provider value={{ weight: 'regular', mirrored: false }}>
      <RouterProvider router={router} />
    </IconContext.Provider>
  )
}
