# app/frontend/src/

| Folder | What |
|---|---|
| `main.tsx` | Entry: mounts the router |
| `app/` | `router.tsx`: every route |
| `layouts/` | `AppLayout.tsx`: sidebar (menu filtered per role), copilot bar, page container |
| `pages/` | One file per route; `home/` holds the per-role homes, `handover/` the handover workspace tabs |
| `components/` | Feature components and the shared primitives in `ui.tsx` ([components/README.md](components/README.md)) |
| `hooks/` | `useApi` (GET with loading, error, reload), `usePaged`, `useViewAs` (persona, roles, session, read-only setup), `useTour` |
| `lib/` | `api.ts` (the only place that calls `fetch`), `format.ts`, `trace.ts` (X-ray trace ids), `viewAs.ts` |
| `types/` | `api.ts`: response types mirroring the backend |
| `styles/` | `index.css`: Tailwind import and the design tokens |

How to add a page or call a new endpoint: [../README.md](../README.md#adding-a-page).
