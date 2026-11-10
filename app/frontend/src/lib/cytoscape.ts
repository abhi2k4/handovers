import { useEffect, useState } from 'react'
import type cytoscape from 'cytoscape'

// Cytoscape is about half of the app's JavaScript and only draws the Graph X-ray and "How it's
// built" panels. It is fetched the first time one of them opens, never on page load.

type Cytoscape = typeof cytoscape

let loaded: Cytoscape | null = null
let loading: Promise<Cytoscape> | null = null

/** The cytoscape constructor, or null for the moment while it downloads. */
export function useCytoscape(): Cytoscape | null {
  const [lib, setLib] = useState<Cytoscape | null>(loaded)
  useEffect(() => {
    if (lib) return
    let live = true
    loading ??= import('cytoscape').then((m) => (loaded = m.default))
    void loading.then((c) => {
      if (live) setLib(() => c)
    })
    return () => {
      live = false
    }
  }, [lib])
  return lib
}
