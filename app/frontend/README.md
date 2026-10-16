# app/frontend/

React UI for managers, departing employees, successors and reviewers.

**Status:** base app ready: routing, layout, theme, UI primitives, typed API client, and a home
page with live backend and FalkorDB status.

## Routes

One site, one build:

| Path | What |
|---|---|
| `/` | Landing page (`src/landing/`: its own look, scoped under `.landing` in `landing/landing.css`) |
| `/dashboard/*` | The app (`src/app/router.tsx`, react-router `basename` = `APP_BASE` in `src/app/base.ts`). `/dashboard/policy`: the company's exit policy and the background job queue (HR, platform admin) |
| anything else | An older app link (`/handovers/…`, `/login` from Keycloak's logout): forwarded to `/dashboard/…` |

`src/main.tsx` picks the side; each is lazy-loaded, so app visitors never download the landing
page's animation code. Inside the app, links stay app-relative (`/handovers/x`); the router adds
`/dashboard`. The backend builds absolute app links with `Settings.app_url()`.

Landing assets live in `src/landing/art/`: two photographs from Unsplash (Unsplash licence) and one
real capture of this app, as WebP. General Sans (Fontshare, ITF FFL) and Newsreader (Google Fonts,
OFL) are self-hosted in `src/landing/fonts/`. Landing sections, top to bottom: Hero, Problem,
Product, HowItWorks, Memory, Outro. Problem, Product and HowItWorks are pinned scroll scenes
(`components/Scene.tsx`, one snap point per screen of scroll); their copy and the benchmark
questions come from the sample company and live in `src/landing/story.ts`.

## Run on the host (dev, hot reload)

Prerequisites: Node.js ≥ 22.12 with npm, and the backend running on port 8000 (see
[app/backend](../backend/README.md)). If the full Docker stack is up, stop its frontend first:
`docker compose stop frontend`.

**bash**
```bash
cd app/frontend
npm install
npm run dev
```
**PowerShell**
```powershell
cd app\frontend
npm install
npm run dev
```

Landing page: http://localhost:5173 · App: http://localhost:5173/dashboard. The browser calls `/api/*` on the same origin, and Vite forwards
those calls to `http://127.0.0.1:8000` (`BACKEND_PORT` in the root `.env`). In Docker, nginx does
the same forwarding.

## Checks

Same commands in bash and PowerShell (inside `app/frontend`):
```
npm run typecheck   # tsc
npm run lint        # oxlint
npm run build       # production build into dist/
```

**Accessibility (WCAG 2.2 AA):** with `npm run dev` running, open a page and paste this in the
browser console. It loads `axe-core` (a dev dependency) from the dev server and lists violations:
```js
const s = document.createElement('script'); s.src = '/node_modules/axe-core/axe.min.js'; document.head.appendChild(s)
await new Promise((r) => (s.onload = r))
;(await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] } })).violations
```
Automated checks catch contrast, names and roles; keyboard flow and screen-reader wording still need
a person.

## Roles and "View as"

The account switcher at the foot of the sidebar (**View as**) sets a demo identity (stored in the browser, sent as the
`X-View-As` header by `lib/api.ts`). Home, menu and pages follow the person's roles
(`hooks/useViewAs.ts`); the backend enforces the same rules. "Everyone (no restrictions)" shows the
full app. Screens per role: [docs/product-strategy.md §10](../../docs/product-strategy.md#10-in-app-user-flow).

## Graph X-ray

The **Graph X-ray** button next to the copilot bar opens a panel with the named Cypher queries
FalkorDB ran for the current page (`lib/trace.ts` collects trace ids from API responses) and, on a
person, handover or your home, an interactive Cytoscape.js picture of the graph around it.

## How it's built

The **How it's built** button in the sidebar opens the project's own architecture as a graph, read
from the FalkorDB graph `handovers_project` (`components/TechGraph.tsx`, `GET /api/xray/project`;
[graph/project/](../../graph/project/README.md)). Visible to everyone, judges included.

## Structure

```
src/
  main.tsx              entry: mounts <RouterProvider>
  app/router.tsx        all routes (pages render inside AppLayout)
  layouts/AppLayout.tsx sidebar, page container, scroll restoration, page fade
  layouts/nav.ts        the app's pages and who may open them (sidebar and ⌘K menu share it)
  pages/                one file per route: HomePage (picks the home per role), LoginPage,
                        OverviewPage, InsightsPage (KPIs), AccountsPage, PeoplePage, PersonPage,
                        HandoversPage, AskPage, SourcesPage, IntegrationsPage, NotFoundPage
  pages/home/           EmployeeHome, LeaverHome, SuccessorHome, ManagerHome
  pages/handover/       the handover workspace and its tabs
  components/           feature components (components/README.md): ViewAs, Xray, TechGraph, ...
  components/ui.tsx     shared primitives: Card, Stat, Bar, Chip, Button, ...
  hooks/                useApi (GET with reload), useViewAs (current persona and roles)
  lib/                  api.ts (the only place that calls fetch), viewAs.ts, format.ts
  types/api.ts          API response types (mirror the backend)
  styles/index.css      Tailwind import + design tokens
```

### Adding a page

1. Create `src/pages/MyPage.tsx`.
2. Register it in `src/app/router.tsx` (`{ path: 'my-page', element: <MyPage /> }`).
3. Optionally add it to `nav` in `src/layouts/AppLayout.tsx` (set `roles` to limit who sees it).

### Calling a new endpoint

1. Add the response type to `src/types/api.ts`.
2. Add a method to `api` in `src/lib/api.ts`.
3. Wrap it in a hook in `src/hooks/` if a component needs loading/error state.

## Theme

A record-keeping look, built from the logo's colours (`src/styles/index.css`): small radii (2 px tags,
4 px controls, 6 px cards, 8 px dialogs), hairlines instead of shadows, square status tags with a
colour marker (`Chip`), square avatars tinted per person, and Geist Mono for labels, ids and figures
(the `eyebrow` utility: small caps, used for stat labels, column heads and menu groups). Use the
tokens, never raw hex values:

| Token | Use | Value |
|---|---|---|
| `ink`, `ink-2`, `ink-3` | text: primary, secondary, quiet | logo navy `#0f1b2d`, `#4a5568`, `#637082` |
| `accent`, `accent-fill`, `accent-hover`, `accent-soft` | links, primary buttons, focus, selection | logo blue `#1c64d8` / `#1f6feb` |
| `ok`, `ok-text`, `ok-soft` | done, handed over | logo teal, darkened for contrast `#0f7a5f` |
| `risk-*`, `soon-*` | risk and deadlines, always with words | red, amber |
| `page`, `app`, `hover`, `selected`, `line`, `control` | surfaces and borders | white and cool slate greys |
| `s1`-`s4` | single-series charts | logo blue in four steps |
| `c1`-`c4` | categorical charts (work, accounts, contacts, knowledge) | blue, orange, aqua, violet; order checked for colour-blind separation, always with a legend |
| `shadow-card`, `shadow-raised` | cards; things that float (menus) | a hairline; a hairline plus a soft shadow |

Layout: slate sidebar, white canvas, white cards with hairlines. Key numbers sit in one instrument
panel split by hairlines (`StatBand`: small-caps label, value, note, a short tone rule on top, and a
meter against target or a sparkline); `variant="band"` is the compact form for
numbers inside a card. Charts live in `components/charts.tsx`: `ColumnChart`, `StackBar`, `Donut` /
`Breakdown` (part-to-whole with legend), `Gauge` (percentage ring with target tick), `HBars` (labelled
bars with a target line), `StepBars` (counts per pipeline stage), `Sparkline`. They are plain SVG and
CSS, no chart library. The sidebar fits a 680px-tall window without scrolling.

**Dark mode.** The theme button next to Graph X-ray offers Light, Dark or Match system (kept in this
browser, `lib/theme.ts`). It puts a `dark` class on `<html>`, applied before the first paint, and
`:root.dark` in `styles/index.css` re-points every colour token, so components never branch on the
theme: use tokens (`text-on-ink` for text on an ink-filled surface) and, for the rare hard-coded tint,
a `dark:` variant. The canvas graphs (Graph X-ray, How it's built) take their colours from
`graphInk(theme)`. The landing page never gets the class. Printing always uses the light colours.

Every text colour passes WCAG AA (4.5:1) on its background, in both themes. Body text is 14px.

Fonts: Geist and Geist Mono, self-hosted through `@fontsource-variable/geist` and
`@fontsource-variable/geist-mono` (no request to Google Fonts).
Icons: Phosphor (MIT), imported one file per icon through `src/components/icons.ts`, so screens never
import the icon package directly. Logos come from [`assets/logos`](../../assets/README.md), which
Vite serves at the site root (`/logo-mark.png`).

## Stack

React 19 · React Router 7 · Vite 8 · TypeScript · Tailwind CSS 4 · oxlint.

React Router 8 needs Node ≥ 22.22, so we stay on 7 until the team's Node versions are upgraded.

Design: [`../../docs/architecture.md`](../../docs/architecture.md#t-frontend-information-architecture).
