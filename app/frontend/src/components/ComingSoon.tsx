import { PlatformLogo } from './PlatformLogo'

/** Platforms on the way: shown so admins know what is next, not connectable yet. */
export function ComingSoon({ items }: { items: { id: string; name: string; label: string }[] }) {
  return (
    <ul className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-2" aria-label="Coming soon">
      {items.map((p) => (
        <li key={p.id} className="flex items-center gap-3 rounded-[6px] bg-page px-4 py-3 shadow-[inset_0_0_0_1px_var(--color-line)]">
          <PlatformLogo id={p.id} name={p.name} muted />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[14px] font-medium text-ink-2">{p.name}</span>
            <span className="block text-[12px] text-ink-3">{p.label} · Coming soon</span>
          </span>
        </li>
      ))}
    </ul>
  )
}
