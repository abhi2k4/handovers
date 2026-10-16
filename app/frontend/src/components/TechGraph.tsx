import cytoscape from 'cytoscape'
import { useEffect, useMemo, useRef, useState } from 'react'
import { graphInk, useTheme } from '../lib/theme'
import { createPortal } from 'react-dom'
import { Network, X } from './icons'
import { useApi } from '../hooks/useApi'
import { Segmented } from './ui'

/* "How it's built": the project's own architecture, read live from the FalkorDB graph
   handovers_project (backend services/tech_graph.py, graph/project/architecture.json). */

interface Component {
  id: string
  name: string
  kind: string
  summary: string
  path: string
}

interface ProjectGraph {
  graph: string
  nodes: Component[]
  links: { source: string; target: string; how: string }[]
  cypher: string
}

/** Left to right, the way a request travels: browser, app, API, logic, data, the outside. */
const LAYERS: { kind: string; label: string; color: string }[] = [
  { kind: 'client', label: 'Browser', color: '#6b7280' },
  { kind: 'frontend', label: 'Frontend', color: '#0e7490' },
  { kind: 'api', label: 'API', color: '#2563eb' },
  { kind: 'service', label: 'Services', color: '#7c3aed' },
  { kind: 'core', label: 'Core', color: '#9333ea' },
  { kind: 'graph', label: 'Graph assets', color: '#c2410c' },
  { kind: 'store', label: 'Databases', color: '#dc2626' },
  { kind: 'connector', label: 'Connectors', color: '#15803d' },
  { kind: 'identity', label: 'Sign-in', color: '#0f766e' },
  { kind: 'external', label: 'Outside services', color: '#475569' },
]
const LAYER = new Map(LAYERS.map((l, i) => [l.kind, { ...l, index: i }]))

export function TechGraphButton() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="How Handovers is built, as a graph in FalkorDB"
        className="flex h-8 min-w-0 items-center gap-1.5 rounded-[4px] px-1.5 text-[13px] whitespace-nowrap text-ink-2 transition-colors duration-150 hover:bg-hover hover:text-ink"
      >
        <Network size={16} className="shrink-0 text-accent" />
        How it&apos;s built
      </button>
      {/* Portal: an ancestor with backdrop-filter would otherwise trap this fixed-position panel. */}
      {open && createPortal(<TechGraphPanel onClose={() => setOpen(false)} />, document.body)}
    </>
  )
}

function TechGraphPanel({ onClose }: { onClose: () => void }) {
  const { data, error, loading } = useApi<ProjectGraph>('/xray/project')
  const [tab, setTab] = useState<'graph' | 'cypher'>('graph')
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 md:p-6" role="dialog" aria-modal="true" aria-label="How Handovers is built">
      <button aria-label="Close" onClick={onClose} className="absolute inset-0 cursor-default bg-[rgba(15,27,45,0.28)]" />
      <div className="relative flex h-full w-full max-w-[1280px] flex-col overflow-hidden bg-page shadow-[0_24px_64px_rgba(15,27,45,0.24)] md:rounded-[8px]">
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
          <div>
            <h2 className="flex items-center gap-2 text-[17px] font-semibold">
              <Network size={18} className="text-accent" /> How Handovers is built
            </h2>
            <p className="mt-1 text-[13px] text-ink-3">
              {data
                ? `${data.nodes.length} components and ${data.links.length} links, read just now from the FalkorDB graph ${data.graph} with one named, read-only query. Click a component.`
                : 'The architecture of this app, stored as a graph in FalkorDB.'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Segmented
              value={tab}
              onChange={setTab}
              options={[
                { value: 'graph', label: 'Graph' },
                { value: 'cypher', label: 'Cypher' },
              ]}
            />
            <button onClick={onClose} aria-label="Close" className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-ink">
              <X size={16} />
            </button>
          </div>
        </header>

        {loading && !data && <p className="p-6 text-ink-3">Reading the project graph…</p>}
        {error && <p className="p-6 text-risk-text">{error}</p>}
        {data && tab === 'cypher' && (
          <div className="overflow-y-auto p-6">
            <p className="mb-3 text-[14px] text-ink-2">
              The query behind this view, from <code className="font-mono text-[13px]">graph/queries/project_graph.cypher</code>, run with
              GRAPH.RO_QUERY. The product&apos;s own screens use the same catalogue: open Graph X-ray on any page to see theirs.
            </p>
            <pre className="overflow-x-auto rounded-[6px] bg-app p-4 font-mono text-[12.5px] leading-relaxed text-ink shadow-[inset_0_0_0_1px_var(--color-line)]">
              {data.cypher}
            </pre>
          </div>
        )}
        {data && tab === 'graph' && (
          <div className="flex min-h-0 flex-1 flex-col md:flex-row">
            <div className="relative h-[420px] min-w-0 flex-1 md:h-auto">
              <Canvas data={data} selected={selected} onSelect={setSelected} />
              <Legend />
            </div>
            <Details data={data} id={selected} onSelect={setSelected} />
          </div>
        )}
      </div>
    </div>
  )
}

/** Columns by layer; within a column, evenly spaced and centred. */
function positions(nodes: Component[]): Map<string, { x: number; y: number }> {
  const columns = new Map<number, Component[]>()
  for (const n of nodes) {
    const index = LAYER.get(n.kind)?.index ?? LAYERS.length
    columns.set(index, [...(columns.get(index) ?? []), n])
  }
  const out = new Map<string, { x: number; y: number }>()
  for (const [index, members] of columns) {
    members.sort((a, b) => a.name.localeCompare(b.name))
    members.forEach((n, row) => out.set(n.id, { x: index * 150, y: (row - (members.length - 1) / 2) * 50 }))
  }
  return out
}

function Canvas({ data, selected, onSelect }: { data: ProjectGraph; selected: string | null; onSelect: (id: string | null) => void }) {
  const { theme } = useTheme()
  const box = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  useEffect(() => {
    if (!box.current) return
    const pos = positions(data.nodes)
    const ink = graphInk(theme)
    const cy = cytoscape({
      container: box.current,
      elements: [
        ...data.nodes.map((n) => ({
          data: { id: n.id, label: n.name, color: LAYER.get(n.kind)?.color ?? '#64748b' },
          position: pos.get(n.id),
        })),
        ...data.links.map((l, i) => ({ data: { id: `e${i}`, source: l.source, target: l.target, label: l.how } })),
      ],
      layout: { name: 'preset', padding: 24 },
      wheelSensitivity: 0.2,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (n: cytoscape.NodeSingular) => n.data('color') as string,
            width: 16,
            height: 16,
            label: 'data(label)',
            'font-size': 12,
            'font-family': 'Geist Variable, system-ui, sans-serif',
            color: ink.text,
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'text-wrap': 'wrap',
            'text-max-width': '130px',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': ink.edge,
            'target-arrow-color': ink.edge,
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.7,
            'curve-style': 'bezier',
          },
        },
        { selector: '.faded', style: { opacity: 0.15 } },
        {
          selector: 'edge.lit',
          style: { 'line-color': ink.accent, 'target-arrow-color': ink.accent, width: 1.6, label: 'data(label)', 'font-size': 9, color: ink.accent, 'text-background-color': ink.surface, 'text-background-opacity': 1 },
        },
        { selector: 'node.lit', style: { width: 18, height: 18, 'border-width': 3, 'border-color': ink.ring } },
      ],
    })
    cy.on('tap', 'node', (e) => onSelect((e.target as cytoscape.NodeSingular).id()))
    cy.on('tap', (e) => e.target === cy && onSelect(null))
    cyRef.current = cy
    return () => cy.destroy()
  }, [data, onSelect, theme])

  // Highlight the selected component and its direct links; fade the rest.
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.elements().removeClass('faded lit')
    if (!selected) return
    const node = cy.getElementById(selected)
    const near = node.closedNeighborhood()
    cy.elements().not(near).addClass('faded')
    near.addClass('lit')
  }, [selected])

  // Cytoscape sets the container to position: relative, so it is sized directly, not by inset.
  return <div ref={box} className="h-full w-full" aria-label="Architecture graph" />
}

function Legend() {
  return (
    <ul className="pointer-events-none absolute bottom-3 left-3 flex max-w-[calc(100%-24px)] flex-wrap gap-x-3 gap-y-1 rounded-[6px] bg-page/90 px-3 py-2 text-[12px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)]">
      {LAYERS.map((l) => (
        <li key={l.kind} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: l.color }} aria-hidden />
          {l.label}
        </li>
      ))}
    </ul>
  )
}

function Details({ data, id, onSelect }: { data: ProjectGraph; id: string | null; onSelect: (id: string) => void }) {
  const byId = useMemo(() => new Map(data.nodes.map((n) => [n.id, n])), [data])
  const node = id ? byId.get(id) : null

  if (!node) {
    return (
      <aside className="w-full shrink-0 border-t border-line p-5 text-[14px] text-ink-2 md:w-[320px] md:border-t-0 md:border-l">
        <h3 className="mb-2 text-[15px] font-semibold text-ink">Reading the graph</h3>
        <p className="mb-2">Each dot is a part of the system; each arrow says how one uses another. Columns follow a request from the browser to the database and out to the tools Handovers learns from.</p>
        <p className="text-ink-3">FalkorDB is the primary database: the company graph holds people, work, knowledge and handovers; this project graph holds the architecture itself.</p>
      </aside>
    )
  }
  const out = data.links.filter((l) => l.source === node.id)
  const into = data.links.filter((l) => l.target === node.id)
  const layer = LAYER.get(node.kind)

  return (
    <aside className="w-full shrink-0 overflow-y-auto border-t border-line p-5 text-[14px] md:w-[320px] md:border-t-0 md:border-l">
      <p className="flex items-center gap-1.5 text-[12px] font-medium tracking-wide text-ink-3 uppercase">
        <span className="size-2.5 rounded-full" style={{ background: layer?.color }} aria-hidden />
        {layer?.label ?? node.kind}
      </p>
      <h3 className="mt-1 text-[17px] font-semibold">{node.name}</h3>
      <p className="mt-2 text-ink-2">{node.summary}</p>
      {node.path && <code className="mt-3 block truncate rounded-[4px] bg-app px-2 py-1 font-mono text-[12px] text-ink-2">{node.path}</code>}
      <LinkList title="Uses" links={out.map((l) => ({ id: l.target, how: l.how }))} byId={byId} onSelect={onSelect} />
      <LinkList title="Used by" links={into.map((l) => ({ id: l.source, how: l.how }))} byId={byId} onSelect={onSelect} />
    </aside>
  )
}

function LinkList({
  title,
  links,
  byId,
  onSelect,
}: {
  title: string
  links: { id: string; how: string }[]
  byId: Map<string, Component>
  onSelect: (id: string) => void
}) {
  if (!links.length) return null
  return (
    <div className="mt-4">
      <h4 className="mb-1.5 text-[13px] font-medium text-ink-3">{title}</h4>
      <ul className="flex flex-col gap-1">
        {links.map((l) => (
          <li key={`${l.id}-${l.how}`}>
            <button onClick={() => onSelect(l.id)} className="w-full rounded-[4px] px-2 py-1 text-left hover:bg-hover">
              <span className="font-medium">{byId.get(l.id)?.name ?? l.id}</span>
              <span className="text-ink-3"> · {l.how}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
