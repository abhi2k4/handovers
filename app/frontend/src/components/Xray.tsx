import cytoscape from 'cytoscape'
import { ArrowLeft, ChevronRight, Copy, ScanSearch, X } from './icons'
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation } from 'react-router'
import { useApi } from '../hooks/useApi'
import { useViewAs } from '../hooks/useViewAs'
import { currentTraces, startPage, subscribe } from '../lib/trace'
import { graphInk, useTheme } from '../lib/theme'
import { Segmented } from './ui'

interface TracedQuery {
  name: string
  label: string | null
  params: Record<string, unknown>
  rows: number
  ms: number
  mode: 'read' | 'write'
  cypher: string
}

interface Trace {
  id: string
  method: string
  path: string
  ms: number
  queries: TracedQuery[]
}

interface Subgraph {
  root: string
  nodes: { id: string; kind: string; label: string }[]
  edges: { source: string; target: string; type: string }[]
  truncated: boolean
}

/** The node the current page is about, for the Graph tab. */
function subjectOf(path: string, search: string, me: string | null): string | null {
  const [, first, second] = path.split('/')
  if (first === 'people' && second) return decodeURIComponent(second)
  if (first === 'handovers' && second) return decodeURIComponent(second)
  // Ask: the person whose memory answers, e.g. the successor's knowledge inherited from the leaver.
  if (first === 'ask') return new URLSearchParams(search).get('as') || me
  if ((path === '/' || path === '/me') && me) return me
  return null
}

/** "Graph X-ray": the Cypher behind this screen and the graph around its subject. */
export function XrayButton() {
  const location = useLocation()
  const [open, setOpen] = useState(false)

  // New page: only its own requests are shown.
  useEffect(() => startPage(location.pathname), [location.pathname])

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Graph X-ray: see the FalkorDB queries behind this screen"
        className="flex h-10 shrink-0 items-center gap-1.5 rounded-[6px] bg-page px-3 text-[14px] font-medium text-ink-2 shadow-[inset_0_0_0_1px_var(--color-control),0_1px_2px_rgba(15,27,45,0.04)] transition-colors hover:bg-hover hover:text-ink"
      >
        <ScanSearch size={15} strokeWidth={1.75} className="text-accent" />
        <span className="max-sm:sr-only">Graph X-ray</span>
      </button>
      {/* Portal: an ancestor with backdrop-filter would otherwise trap this fixed-position panel. */}
      {open && createPortal(<XrayPanel path={location.pathname} search={location.search} onClose={() => setOpen(false)} />, document.body)}
    </>
  )
}

function XrayPanel({ path, search, onClose }: { path: string; search: string; onClose: () => void }) {
  const { me } = useViewAs()
  const subject = subjectOf(path, search, me?.id ?? null)
  const [tab, setTab] = useState<'queries' | 'graph'>('queries')
  const [closing, setClosing] = useState(false)

  const handleClose = useCallback(() => {
    if (closing) return
    setClosing(true)
    setTimeout(onClose, 240)
  }, [closing, onClose])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && handleClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [handleClose])

  return (
    <div className="fixed inset-0 z-50 flex justify-end overflow-hidden" role="dialog" aria-modal="true" aria-label="Graph X-ray">
      <button
        aria-label="Close"
        onClick={handleClose}
        className={`absolute inset-0 cursor-default bg-[rgba(15,27,45,0.24)] transition-opacity duration-200 ease-out ${
          closing ? 'opacity-0' : 'backdrop-fade-in'
        }`}
      />
      <div
        className={`relative flex h-full w-full max-w-[680px] flex-col bg-page shadow-[-8px_0_32px_rgba(15,27,45,0.16)] ${
          closing ? 'translate-x-full transition-transform duration-200 ease-in' : 'tray-slide-in'
        }`}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
          <div>
            <h2 className="flex items-center gap-2 text-[17px] font-semibold">
              <ScanSearch size={17} strokeWidth={1.75} className="text-accent" /> Graph X-ray
            </h2>
            <p className="mt-1 text-[13px] text-ink-3">
              The named Cypher queries FalkorDB ran for this screen, and the graph around it. Read-only.
            </p>
          </div>
          <button onClick={handleClose} aria-label="Close" className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-ink">
            <X size={16} />
          </button>
        </header>
        <div className="px-6 pt-4">
          <Segmented
            value={tab}
            onChange={setTab}
            options={[
              { value: 'queries', label: 'Queries' },
              { value: 'graph', label: 'Graph' },
            ]}
          />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          {tab === 'queries' ? <Queries /> : subject ? <GraphView id={subject} /> : <p className="text-ink-3">This page has no single subject. Open a person, a handover or your home to see its graph.</p>}
        </div>
      </div>
    </div>
  )
}

function Queries() {
  const traces = useSyncExternalStore(subscribe, currentTraces)
  if (traces.length === 0) return <p className="text-ink-3">No API calls recorded on this page yet.</p>
  return (
    <div className="flex flex-col gap-5">
      {/* Newest first: the action just taken (an answer, an approval) is what people open this for. */}
      {[...traces].reverse().map((t) => (
        <TraceView key={t.id} id={t.id} />
      ))}
    </div>
  )
}

function TraceView({ id }: { id: string }) {
  const { data: t, error } = useApi<Trace>(`/xray/${id}`)
  if (error) return <p className="text-[13px] text-ink-3">{error}</p>
  if (!t || t.queries.length === 0) return null
  const total = t.queries.reduce((n, q) => n + q.ms, 0)
  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between gap-3 text-[13px]">
        <code className="font-medium text-ink">
          {t.method} {t.path}
        </code>
        <span className="num text-ink-3">
          {t.queries.length} queries · {total.toFixed(1)} ms in FalkorDB
        </span>
      </div>
      <ul className="flex flex-col gap-2">
        {t.queries.map((q, i) => (
          <QueryView key={`${q.name}-${i}`} q={q} />
        ))}
      </ul>
    </section>
  )
}

const CYPHER_KEYWORDS = new Set(
  'MATCH OPTIONAL WHERE RETURN WITH ORDER BY LIMIT SKIP AS AND OR NOT XOR CASE WHEN THEN ELSE END MERGE SET CREATE DELETE DETACH REMOVE UNWIND DISTINCT IN IS NULL TRUE FALSE CALL YIELD ON DESC ASC STARTS ENDS CONTAINS EXISTS'.split(' '),
)

/** Light Cypher colouring: keywords, parameters, strings and comments. Text only, no HTML. */
function Cypher({ text }: { text: string }) {
  return (
    <pre className="overflow-x-auto font-mono text-[12px] leading-[17px] whitespace-pre text-ink-2">
      {text.split('\n').map((line, i) => {
        if (line.trim().startsWith('//')) {
          return (
            <div key={i} className="text-ink-3 italic">
              {line}
            </div>
          )
        }
        return (
          <div key={i}>
            {line.split(/(\$\w+|'[^']*'|\b[A-Za-z_]+\b)/).map((part, j) => {
              if (part.startsWith('$')) return <span key={j} className="text-soon">{part}</span>
              if (part.startsWith("'")) return <span key={j} className="text-ok-text">{part}</span>
              if (CYPHER_KEYWORDS.has(part.toUpperCase()) && part === part.toUpperCase())
                return <span key={j} className="font-semibold text-accent">{part}</span>
              return <span key={j}>{part}</span>
            })}
          </div>
        )
      })}
    </pre>
  )
}

function QueryView({ q }: { q: TracedQuery }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  return (
    <li className="overflow-hidden rounded-[4px] shadow-[inset_0_0_0_1px_var(--color-line)]">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-hover">
        <span className="flex min-w-0 items-center gap-2">
          <ChevronRight size={13} className={`shrink-0 text-ink-3 transition-transform ${open ? 'rotate-90' : ''}`} />
          <code className="truncate font-mono text-[13px] text-ink">{q.name}</code>
          {q.mode === 'write' && <span className="rounded-[4px] bg-soon-soft px-1.5 text-[11px] font-semibold text-soon">WRITE</span>}
        </span>
        <span className="num shrink-0 text-[13px] text-ink-3">
          {q.rows} {q.rows === 1 ? 'row' : 'rows'} · {q.ms} ms
        </span>
      </button>
      {open && (
        <div className="border-t border-line bg-app px-3 py-3">
          <div className="mb-2 flex justify-end">
            <button
              onClick={() => {
                void navigator.clipboard?.writeText(q.cypher).then(() => setCopied(true))
              }}
              className="flex items-center gap-1 rounded-[4px] px-1.5 py-0.5 text-[12px] text-ink-3 hover:bg-hover hover:text-ink"
            >
              <Copy size={11} /> {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <Cypher text={q.cypher} />
          {Object.keys(q.params).length > 0 && (
            <div className="mt-3 border-t border-line pt-2 font-mono text-[12px] text-ink-3">
              {Object.entries(q.params).map(([k, v]) => (
                <div key={k}>
                  <span className="text-soon">${k}</span> = {JSON.stringify(v)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </li>
  )
}

/* ------------------------------------------------------------------ graph */

interface Group {
  key: string
  label: string
  color: string
  kinds: string[]
}

// Sectors around the subject, clockwise from the top. Evidence is off by default.
const GROUPS: Group[] = [
  { key: 'work', label: 'Work', color: '#30a46c', kinds: ['Responsibility'] },
  { key: 'accounts', label: 'Accounts', color: '#e5484d', kinds: ['Account'] },
  { key: 'contacts', label: 'Contacts', color: '#ab6400', kinds: ['Stakeholder'] },
  { key: 'knowledge', label: 'Knowledge', color: '#6e56cf', kinds: ['Claim', 'Decision', 'Procedure'] },
  { key: 'handover', label: 'Handover', color: '#e2a336', kinds: ['Handover', 'Gap', 'Transfer', 'Approval'] },
  { key: 'people', label: 'People & team', color: '#0d74ce', kinds: ['Employee', 'Team', 'Role', 'Skill', 'Area'] },
  {
    key: 'evidence',
    label: 'Evidence',
    color: '#8d8d86',
    kinds: ['EOD', 'Message', 'Ticket', 'PullRequest', 'Meeting', 'Document', 'Upload', 'CRMNote', 'InterviewAnswer'],
  },
]
const OTHER: Group = { key: 'other', label: 'Other', color: '#8d8d86', kinds: [] }

const KIND_NAME: Record<string, string> = {
  EOD: 'Daily report',
  PullRequest: 'Pull request',
  CRMNote: 'CRM note',
  InterviewAnswer: 'Interview answer',
  Stakeholder: 'Contact',
  Responsibility: 'Responsibility',
}

function groupOf(kind: string): Group {
  return GROUPS.find((g) => g.kinds.includes(kind)) ?? OTHER
}

function kindName(kind: string): string {
  return KIND_NAME[kind] ?? kind
}

function relationName(type: string): string {
  return type.toLowerCase().replaceAll('_', ' ')
}

/** Place nodes in one sector per group around the subject; alternate two rings in busy sectors. */
function layout(nodes: Subgraph['nodes'], root: string): Map<string, { x: number; y: number; side: 'left' | 'right' }> {
  const pos = new Map<string, { x: number; y: number; side: 'left' | 'right' }>()
  pos.set(root, { x: 0, y: 0, side: 'right' })
  const others = nodes.filter((n) => n.id !== root)
  const groups = [...GROUPS, OTHER]
    .map((g) => ({ g, items: others.filter((n) => groupOf(n.kind) === g) }))
    .filter((x) => x.items.length > 0)
  const total = groups.reduce((n, x) => n + Math.max(2, x.items.length), 0)
  let angle = -Math.PI / 2
  for (const { items } of groups) {
    const span = (2 * Math.PI * Math.max(2, items.length)) / total
    items.forEach((n, i) => {
      const a = angle + (span * (i + 0.5)) / items.length
      const r = items.length > 6 && i % 2 === 1 ? 250 : 190
      pos.set(n.id, { x: r * Math.cos(a), y: r * Math.sin(a), side: Math.cos(a) < 0 ? 'left' : 'right' })
    })
    angle += span
  }
  return pos
}

/** Under a persona only people and handovers can be re-centred on (the API checks the same). */
function explorable(persona: string, nid: string): boolean {
  return !persona || nid.startsWith('emp:') || nid.startsWith('ho:')
}

interface Picked {
  id: string
  kind: string
  label: string
  relation: string | null
}

function GraphView({ id: start }: { id: string }) {
  const [history, setHistory] = useState<string[]>([start])
  const id = history[history.length - 1]
  const { data: g, error, loading } = useApi<Subgraph>(`/xray/subgraph?id=${encodeURIComponent(id)}`)
  const [hidden, setHidden] = useState<Set<string>>(() => new Set(['evidence']))
  const [picked, setPicked] = useState<Picked | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const { persona } = useViewAs()
  const { theme } = useTheme()

  useEffect(() => {
    if (!g || !box.current) return
    const visible = g.nodes.filter((n) => n.id === g.root || !hidden.has(groupOf(n.kind).key))
    const ids = new Set(visible.map((n) => n.id))
    const pos = layout(visible, g.root)
    const ink = graphInk(theme)
    const relationTo = new Map(g.edges.map((e) => [e.source === g.root ? e.target : e.source, e]))
    const cy = cytoscape({
      container: box.current,
      elements: [
        ...visible.map((n) => ({
          data: {
            id: n.id,
            label: n.label,
            kind: n.kind,
            color: n.id === g.root ? ink.root : groupOf(n.kind).color,
            root: n.id === g.root ? 1 : 0,
            side: pos.get(n.id)?.side ?? 'right',
          },
          position: { x: pos.get(n.id)?.x ?? 0, y: pos.get(n.id)?.y ?? 0 },
        })),
        ...g.edges
          .filter((e) => ids.has(e.source) && ids.has(e.target))
          .map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target, type: relationName(e.type) } })),
      ],
      layout: { name: 'preset', padding: 30 },
      minZoom: 0.4,
      maxZoom: 2.5,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (n: cytoscape.NodeSingular) => n.data('color') as string,
            width: 12,
            height: 12,
            label: 'data(label)',
            'font-family': 'Inter, system-ui, sans-serif',
            'font-size': 10,
            color: ink.text,
            'text-valign': 'center',
            'text-halign': (n: cytoscape.NodeSingular) => (n.data('side') === 'left' ? 'left' : 'right'),
            'text-margin-x': (n: cytoscape.NodeSingular) => (n.data('side') === 'left' ? -6 : 6),
            'text-max-width': '130px',
            'text-wrap': 'ellipsis',
            'border-width': 2,
            'border-color': ink.surface,
          },
        },
        {
          selector: 'node[root = 1]',
          style: {
            width: 30,
            height: 30,
            'font-size': 12,
            'font-weight': 'bold',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-x': 0,
            'text-margin-y': 6,
          },
        },
        { selector: 'node:selected', style: { 'border-color': ink.accent, 'border-width': 3 } },
        {
          selector: 'edge',
          style: { width: 1, 'line-color': ink.edge, 'curve-style': 'straight', 'target-arrow-shape': 'none' },
        },
        { selector: 'edge.hl', style: { 'line-color': ink.accent, width: 1.5, label: 'data(type)', 'font-size': 9, color: ink.accent, 'text-background-color': ink.surface, 'text-background-opacity': 1, 'text-background-padding': '2px' } },
        { selector: 'node.dim', style: { opacity: 0.35 } },
      ],
    })
    cy.on('tap', 'node', (e) => {
      const n = e.target as cytoscape.NodeSingular
      cy.elements().removeClass('hl dim')
      n.connectedEdges().addClass('hl')
      cy.nodes().not(n.closedNeighborhood()).addClass('dim')
      const rel = relationTo.get(n.id())
      setPicked({
        id: n.id(),
        kind: n.data('kind') as string,
        label: n.data('label') as string,
        relation: rel ? relationName(rel.type) : null,
      })
    })
    cy.on('tap', (e) => {
      if (e.target === cy) {
        cy.elements().removeClass('hl dim')
        setPicked(null)
      }
    })
    cy.on('dbltap', 'node', (e) => {
      const nid = (e.target as cytoscape.NodeSingular).id()
      if (nid !== g.root && explorable(persona, nid)) {
        setPicked(null)
        setHistory((h) => [...h, nid])
      }
    })
    return () => cy.destroy()
  }, [g, hidden, persona, theme])

  if (loading && !g) return <p className="text-ink-3">Loading graph…</p>
  if (error) return <p className="text-ink-3">{error}</p>
  if (!g) return null

  const rootNode = g.nodes.find((n) => n.id === g.root)
  const counts = new Map<string, number>()
  for (const n of g.nodes) if (n.id !== g.root) counts.set(groupOf(n.kind).key, (counts.get(groupOf(n.kind).key) ?? 0) + 1)
  const groups = [...GROUPS, OTHER].filter((gr) => counts.has(gr.key))
  const link = (nid: string) =>
    nid.startsWith('emp:') ? `/people/${encodeURIComponent(nid)}` : nid.startsWith('ho:') ? `/handovers/${encodeURIComponent(nid)}` : null

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-[15px] font-semibold">{rootNode?.label ?? id}</div>
          <div className="text-[13px] text-ink-3">
            {rootNode ? kindName(rootNode.kind) : ''} · {g.nodes.length - 1} connections
            {g.truncated ? ' (first 40)' : ''}
          </div>
        </div>
        {history.length > 1 && (
          <button
            onClick={() => {
              setPicked(null)
              setHistory((h) => h.slice(0, -1))
            }}
            className="flex shrink-0 items-center gap-1 rounded-[4px] px-2 py-1 text-[13px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-control)] hover:bg-hover"
          >
            <ArrowLeft size={12} /> Back
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {groups.map((gr) => {
          const off = hidden.has(gr.key)
          return (
            <button
              key={gr.key}
              onClick={() =>
                setHidden((h) => {
                  const next = new Set(h)
                  if (next.has(gr.key)) next.delete(gr.key)
                  else next.add(gr.key)
                  return next
                })
              }
              aria-pressed={!off}
              className={`flex items-center gap-1.5 rounded-[3px] px-2.5 py-1 text-[12.5px] transition-colors ${
                off ? 'text-ink-3 shadow-[inset_0_0_0_1px_var(--color-line)] hover:text-ink-2' : 'bg-hover text-ink'
              }`}
            >
              <span className="size-2 rounded-full" style={{ background: off ? 'var(--color-mark)' : gr.color }} />
              {gr.label}
              <span className="num text-ink-3">{counts.get(gr.key)}</span>
            </button>
          )
        })}
      </div>

      <div className="relative">
        <div ref={box} className="h-[440px] w-full rounded-[6px] bg-app" aria-label={`Graph around ${id}`} />
        {picked && (
          <div className="absolute right-3 bottom-3 left-3 rounded-[6px] bg-page p-3 shadow-[0_0_0_1px_var(--color-line),0_6px_20px_rgba(15,27,45,0.10)]">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[12px] text-ink-3">{kindName(picked.kind)}</div>
                <div className="truncate text-[14px] font-medium">{picked.label}</div>
                {picked.relation && picked.id !== g.root && (
                  <div className="mt-0.5 text-[13px] text-ink-2">
                    {rootNode?.label} <span className="text-accent">{picked.relation}</span> this
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                {picked.id !== g.root && explorable(persona, picked.id) && (
                  <button
                    onClick={() => {
                      setPicked(null)
                      setHistory((h) => [...h, picked.id])
                    }}
                    className="rounded-[4px] px-2 py-1 text-[13px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-control)] hover:bg-hover"
                  >
                    Explore
                  </button>
                )}
                {link(picked.id) && (
                  <Link to={link(picked.id) ?? '/'} className="rounded-[4px] bg-accent-fill px-2 py-1 text-[13px] text-white hover:bg-accent-hover">
                    Open
                  </Link>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
      <p className="text-[12px] text-ink-3">Click a node for details · double-click or Explore to centre on it · scroll to zoom</p>
    </div>
  )
}
