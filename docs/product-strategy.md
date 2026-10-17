# Product Strategy

Status: agreed direction for the team. Where this doc says **hypothesis**, it needs validation with
customers or pilot data. No outcome metric here is a measured result.

---

## 1. The one-line truth

**Every company loses work knowledge when people move on, and finds out weeks later when something
breaks.** Today the handover is a checklist, a stale job description and a goodbye call. Handovers
makes it a measurable process: the system already knows what the person does, what only they know
and what breaks first. It hands HR the hiring kit and hands the successor a companion that knows
what the predecessor knew.

**Why it can change the category.** Existing tools work on *documents* (ServiceNow's
knowledge-transfer plan is built from documents the leaver authored) or on *search* (Glean,
Atlassian Rovo). None of the tools we surveyed computes **what is at risk
before the person leaves** and turns it into **the job description, the hiring kit and the
successor's memory** in one flow.

**Honest caveat.** The moat is the workflow plus the trust design, not the AI. If an incumbent
copies a "knowledge-transfer plan", we still win on the risk computation and the successor
companion. We do not win on document summarisation.

## 2. Who it is for

**Beachhead (hypothesis):** knowledge-heavy companies with **200 to 5,000 employees**: tech/SaaS,
fintech, digital agencies, IT services (strong in India). They run tools we can connect (Slack or
Teams, Jira, GitHub, Google or Microsoft, a CRM, an HRIS). One departing engineer or performance
marketer can stall a team, and HR hires for roles it cannot evaluate deeply.

**Not first:** frontline and blue-collar workforces (little digital work trail), and companies
under ~100 people (founders already know everything).

| | Who | Why they say yes |
|---|---|---|
| **Economic buyer** | CHRO / VP People | Attrition cost, time to fill, onboarding speed |
| **Co-sponsor** | CTO / VP Engineering, or the business head | Key-person risk, incidents after departures |
| **Must not block** | CISO / IT, Legal / DPO | Access risk, privacy, data residency |

**Pricing hypothesis:** per employee per month across the whole company. Continuous memory and
risk monitoring cover everyone; handovers happen to a few at a time.

## 3. Problems we solve, ranked by pain

| # | Problem | Who feels it | Today | With Handovers |
|---|---|---|---|---|
| 1 | Accounts and access only the leaver controls | IT, Security | Found when something breaks after the last day | Listed on day 0, reassigned before the last day |
| 2 | Recurring work only they do | Manager | Missed deadlines after departure | Plan ordered by next due date |
| 3 | The *why* behind decisions and settings | Successor, team | Asked on Slack after they have gone | Captured by a targeted exit interview |
| 4 | Hiring for a role HR does not understand | HR, recruiter | Old JD copied; interviews are guesswork | JD written from actual work, plus screening and interview kits |
| 5 | Successor ramp-up | Successor, manager | Weeks of digging and asking around | A companion with inherited, cited knowledge |
| 6 | No visibility of risk *before* resignations | Leadership | Invisible | Dashboard: held by one person, backup coverage |

## 4. Users and roles

Every view is permission-scoped by the graph, the same way the companion is today. How identities
and roles reach the app is in [identity-and-access.md](identity-and-access.md). The final role table
(platform admin, HR, IT, manager, exec, employee) is its §0a.

| Role | Who | Sees | Can do | Never sees |
|---|---|---|---|---|
| **Employee** (everyone) | Any staff member | Their own memory: responsibilities, accounts, knowledge, and where each came from | Mark items private, correct or retract facts, add notes or documents | Other people's memory or risk |
| **Leaver** (employee with an open handover) | The person leaving | Their handover: gaps, exit questions, what will and will not transfer | Answer the interview, confirm or edit each answer, keep items private | Manager comments, hiring pipeline |
| **Successor** | New hire, internal mover or cover | Companion, inherited knowledge with lineage, 30/60/90 plan | Ask, flag a wrong answer | The leaver's private items, unapproved knowledge |
| **Manager / Lead** | Direct line manager | Team risk (held by one person, backup coverage), handover workspace for their reports | Approve transfers, assign successors and backups, review the JD | Other teams' detail; anyone's private items |
| **HR / People Ops** | Handover owner | Every handover in scope, HR outputs (JD, screening, interview kit, plan), timeline | Open handovers, generate and export kits, run the process | Content of sensitive knowledge (HR sees counts and status, not content) |
| **Recruiter / TA** | Hiring | JD, screening kit and interview kit for their requisitions | Run the screening checker, send kits to the ATS | Leaver memory, interview answers |
| **IT / Security** | Access owners | Sole-admin accounts and the access transfer checklist | Mark access reassigned or revoked | Knowledge content |
| **Admin / Compliance** | Platform owner, DPO | Audit log, policies, connectors, retention | Configure, export audits, revoke transfers, erase on request | Content, except during a logged investigation |
| **Executive** (read-only) | CXO | Organisation-level KPIs | – | Individual detail |

**Principle:** HR sees process and counts. Knowledge *content* flows only from leaver to successor,
with the manager's approval. That separation is what earns employee trust (and passes works-council
and privacy review).

## 5. We are not the system of record

Nobody will manage employees inside Handovers. **People data comes from the HRIS, identity and
groups from the company's identity provider, work evidence from work tools. Handovers reads; it
never owns them.**

```
HRIS (people, org, roles, resignations) ──┐
Identity provider (SSO, users, groups) ───┼──► Handovers graph ──► outputs back to ATS / ITSM / chat
Work tools (tickets, code, chat, docs) ───┘
```

| Tier | Category | Targets | Pull / push |
|---|---|---|---|
| **P0** | HRIS | Workday, BambooHR, HiBob, Rippling, Personio; India: Darwinbox, Keka, Zoho People | Employees, managers, teams, roles; the **resignation or termination event opens a handover** |
| **P0** | Identity | Microsoft Entra ID, Okta, Google Workspace (via Keycloak, see [identity-and-access.md](identity-and-access.md)) | SSO, users and groups → roles; per-app admin roles → sole-admin accounts |
| **P0** | Chat | Slack, Microsoft Teams | Threads the person took part in; also the channel that **delivers** interview questions and the companion |
| **P1** | Work tracking | Jira, Linear, Asana | Tickets, recurring work, open items |
| **P1** | Code | GitHub, GitLab | Pull requests, reviews, ownership (CODEOWNERS) |
| **P1** | Docs | Confluence, Notion, Google Drive, SharePoint | Where decisions and procedures are written down |
| **P1** | ATS | Greenhouse, Lever, Ashby | **Push** JD, screening criteria and interview scorecards |
| **P2** | CRM | Salesforce, HubSpot | Accounts and stakeholder relationships (sales and marketing roles) |
| **P2** | Calendar | Google, Outlook | Meeting metadata (attendees, topics); never recordings by default |
| **P2** | ITSM / SaaS management | ServiceNow, Jira Service Management, Zluri, BetterCloud | Push access-transfer tasks; read the app inventory |
| **P2** | Incidents | PagerDuty, Opsgenie | On-call and incident ownership |

The hackathon build uses connector-shaped fixtures and the upload screen; the table is the roadmap.

## 6. End-to-end product flow

**Phase 0. Set-up (admin, once).** Connect identity, then the HRIS, then connectors. Set policy:
what is captured, retention, what counts as personal, approval rules. Employees get a notice of
what is remembered and why (a legal requirement in many places, e.g. India's DPDP Act 2023 and
the GDPR in the EU).

**Phase 1. Steady state (everyone, always on).** Memory accrues from work with one attribution rule:
*you hold what you authored, resolved or attended*, not everything you could read. Employees see,
correct and privatise their own memory. Managers and leadership see the risk dashboard and can fix
risk **before** anyone resigns (for example by assigning a backup).

**Phase 2. Trigger.** A resignation in the HRIS sends an event, and a handover opens automatically.
Other triggers: internal move, long leave, re-organisation. Analysis runs at once.

**Phase 3. Notice period** (example: 30-day notice):

| Day | What happens | Who |
|---|---|---|
| D0 | Analysis: what they do, what only they hold, the gaps | System |
| D1 | **Access first:** sole-admin accounts go to IT as tasks | HR → IT |
| D1–3 | JD (with comparison to the old one), screening kit and interview kit go to the ATS; the requisition opens | HR → Recruiter |
| D2–15 | Exit interview: 5–8 targeted questions, asynchronous in Slack or Teams, a few minutes at a time | Leaver |
| Ongoing | Leaver reviews every captured answer, keeps items private | Leaver |
| D−7 | Transfer review: included and excluded with reasons; manager approves | Manager |
| D−5 | Introductions to relationships (stakeholder list with context) | Leaver + successor |
| Last day | Access checklist closed, transfer applied, leaver's memory frozen read-only and retained per policy | System |

**Phase 4. Successor (their D1–D90).** The companion answers from inherited knowledge with sources
and who approved them, says "I don't know, ask X" instead of guessing, and builds a 30/60/90 plan
from the responsibilities. Flagged answers become corrections.

**Phase 5. After.** Audit trail, revocation when needed, outcome KPIs captured at 30, 60 and 90 days.

## 7. KPIs

**North-star metric: share of single-person knowledge resolved before the last day.** Resolved means
a backup was assigned, it was captured in the exit interview, or it was transferred with approval.
It measures exactly the value we promise.

| Layer | KPI | Direction |
|---|---|---|
| **Outcome** (what the buyer pays for) | Successor time to productivity (manager-rated at 30/60/90) | ↓ |
| | Incidents or missed deliverables traced to a departure | ↓ |
| | Time to fill for backfilled roles | ↓ |
| **Outcome, measured today** (completed handovers, `kpi_handover_outcomes`) | Handed over before the last day; knowledge passed on with approval; exit questions answered; sole-admin accounts closed | ↑ |
| **Process** (HR runs on these) | Sole-admin accounts reassigned before the last day | 100% |
| | Exit-interview gaps answered | ↑ |
| | Handovers approved before the last day | ↑ |
| | JD accepted by the hiring manager with few edits | ↑ |
| **Risk** (leadership, continuous) | Work with a backup (responsibilities with ≥ 2 holders) | ↑ |
| | Knowledge with no reason, or with contradictions | ↓ |
| **Product** (us) | Companion answer rate; citation clicks; "this was wrong" flags | ↑ / ↑ / ↓ |
| | Questions answered without contacting the leaver | ↑ |
| **Trust guardrails** | Private-item leaks | 0, always |
| | Employee correction and opt-out rate; trust survey | watch |

Measured today: retrieval quality and leaks in the benchmark ([README results](../README.md#results)).
Everything else needs pilot data.

## 8. Home screen per role

| Role | Home |
|---|---|
| HR | Active handovers by days left and status; overdue steps; kits waiting; exceptions ("sole admin, 5 days left") |
| Manager | Team risk tiles; open handovers; approvals waiting; backup suggestions |
| Leader | Organisation tiles: backup coverage by team and trend, top risks, on-time handovers, outcome KPIs |
| Employee | My memory (counts by type), items to review, privacy controls |
| Leaver | One checklist: questions left, answers to confirm, introductions to make |
| Successor | Companion first; inherited items; 30/60/90 plan; who to ask |
| IT | Sole-admin accounts across open handovers, with due dates |
| Admin | Connector health, sync freshness, audit log, policy |

Today's Overview is the HR / leader home. The other homes are the gap.

## 9. Make-or-break risks

1. **"It's surveillance."** Mitigation: memory only from work artifacts; employees see and correct
   their own; private items excluded; HR sees no content. Product, legal and marketing must say this
   in the same words.
2. **Cold start.** Value must arrive in week 1 from HRIS + Slack/Teams + Jira/GitHub alone.
3. **Wrong answers.** The companion must cite and abstain. It does today; that is our credibility.
4. **Incumbents add a handover feature.** We win as the specialist: risk computation, HR outputs,
   trust design.

## 10. In-app user flow

**One app; your home screen and menu depend on who you are.** Same pages, filtered per role. The
sample company *Northwind* (`graph/seed/northwind/`) provides the cast:

| Person | Story role | Product role |
|---|---|---|
| Nisha Verma (`emp:nisha`) | Performance Marketing Manager, resigning | Leaver |
| Aditi Menon (`emp:aditi`) | Head of Growth, Nisha's manager | Manager |
| Meera Iyer (`emp:meera`) | HR & Admin Lead | HR |
| Ananya Pillai (`emp:ananya`) | Successor | Successor |
| Kavya Rao (`emp:kavya`) | Founder & CEO | Executive |
| (an IT admin) | Owns company accounts | IT |

Parallel engineering story: Arjun (`emp:arjun`) leaves, Farhan (`emp:farhan`) succeeds, Priya
(`emp:priya`) manages.

### 10.1 Two rules the whole flow depends on

1. **HR runs the process but cannot read knowledge content or approve the transfer.** HR sees
   progress and counts ("4 of 9 answered").
2. **Only the leaver's manager approves** what moves to the successor, and **only confirmed,
   non-private** items can move.

### 10.2 What each person sees

**Leaver (Nisha).** Home is **"Your handover"**, a single checklist:
- *Questions only you can answer* (from the gap rules). She answers; the app shows the answer back as
  a structured card ("Decision: …"); **Confirm** or **Edit**. Nothing is saved unconfirmed.
- *What will move to Ananya*, where she can mark any item **private**.
- *People to introduce*: stakeholders only she works with.
- Never sees: hiring (JD, screening, interview kit), manager comments.

**HR (Meera).** Home is the **Overview** dashboard.
- **Start handover**: leaver, last day, successor.
- Handover workspace tabs: Plan, Job description, Screening, Interview kit, Exit interview
  (progress only), Transfer (status only).
- Cannot: approve the transfer, read answers or knowledge content.

**Leadership (Kavya).** Home is **Leadership**, read-only: no Start handover, Reassign or Approve.
- Numbers: held by one person, work with a backup, handovers at risk, handed over before the last day.
- Risk by team (backup coverage), the top single points of failure, and handovers in flight with
  readiness and days left. Any person or handover opens "If they left today": what only they hold.
- Outcomes of completed handovers, measured from the graph (§7). Until one completes they show "–",
  never sample values.
- A leader who is also someone's manager still approves that person's handover from here.

**Manager (Aditi).** Home is **"My team"**: team risk, open handovers, **"Needs your approval"**.
- Same handover tabs as HR, plus **Transfer review**: included and excluded items with reasons;
  **Approve**.
- Sees the leaver's confirmed answers (needed to approve), never items marked private.
- Overview and risk are limited to her own team.

**Successor (Ananya).** Home is **Ask** (the companion) first, plus *What you inherited* (from Nisha,
approved by Aditi), *Your first 30 days* (from the plan), *Who to ask*.
- Before the transfer: "Nothing inherited yet; your handover from Nisha completes on <last day>."
- The companion only reaches her own `KNOWS` edges (already enforced in the queries).

**IT.** Home is **"Accounts to reassign"**: sole-admin accounts across open handovers with due dates;
one **Reassigned** action per account. No knowledge content.

**Executive (Kavya).** Overview, read-only. Organisation numbers only.

**Any employee.** Home is **"My memory"**: what the system holds about their work, with sources;
correct items or mark them private. This is the answer to "is this surveillance?".

### 10.3 Screen map

| Screen | Who sees it | Status |
|---|---|---|
| Overview | HR | Built (Om) |
| **Leadership home** | Executive | **Built**: read-only; risk by team, single points of failure, handovers in flight, measured outcomes |
| **Insights (KPI dashboard, §7)** | HR, executive | **Built**: north star, process, risk and health KPIs from the graph; outcome KPIs measured over completed handovers |
| Manager home ("Your team") | Manager | **Built**: approvals waiting, team members ranked by what only they hold; **"Reduce key-person risk"** adds a backup from the team to work only one teammate does |
| Handover workspace (tabs) | HR, manager | Built; per role: HR sees interview progress only and no Transfer tab; hiring tabs only for HR and the manager. The overview opens with **"Ready by the last day?"**: six checks (successor, accounts, exit interview, job description, ramp-up plan, transfer), each with its owner and a link to fix it |
| Transfer review + Approve | Manager | Built; the API rejects anyone but the leaver's manager |
| Ask (companion) | Everyone (own memory only) | Built; the API rejects asking as someone else |
| People, Sources | HR (people: also executive and managers, managers see their team) | Built |
| **"View as" switcher** | Demo only | **Built** (sidebar) |
| **Successor ramp-up plan** | Manager (create, edit, approve), successor (tick off), HR (view) | **Built**: "Your first 30 days" on the successor home with **"Ask how"** into the companion, review card on the manager home and a Ramp-up plan tab on the handover (§11) |
| **Graph X-ray** | Everyone (own access rules) | **Built**: the Cypher queries behind each screen, and the graph around a person or handover |
| **Leaver home (checklist)** | Leaver | **Built**: questions (reuses the exit interview), what will move, people to introduce |
| **Successor home** | Successor | **Built**: inherited knowledge, handover date, who to ask, link to the companion |
| My memory | Everyone | Built (the person page for yourself; HR sees others without knowledge content) |
| Accounts to reassign | IT (in the sample company: HR & Admin) | **Built**; "Give admin to <successor>" adds the successor as admin and closes the account gap |

Access rules live in one module, `app/backend/services/access.py`; the API reads the demo caller from
the `X-View-As` header (no header = unrestricted, as before).

### 10.4 Identity for the hackathon: "View as"

No real login yet. A **"View as"** switcher (Meera, Aditi, Nisha, Ananya, Kavya, IT, an employee)
sets the caller, and **all "who can see what" rules live in one place in the backend**, keyed by the
caller. Later, Keycloak supplies the caller from a verified login instead of the switcher; nothing
else changes ([identity-and-access.md](identity-and-access.md)). The rules use the job-function role
(HR, IT, executive, employee) plus graph relationships (manager of, leaver of, successor of).

### 10.5 Demo click path (about 3 minutes)

1. **As Kavya:** Overview, "N things held by one person".
2. **As Meera:** Start handover for Nisha; **"Ready by the last day?"** shows what blocks a clean
   exit and who owns each check; **Accounts**: "Give admin to Ananya" closes a sole-admin risk;
   Job description shows what the old JD missed.
3. **As Nisha:** answer one question, confirm the card; mark one item private.
4. **As Ananya:** ask the CAC question: "I don't know yet."
5. **As Aditi:** Needs your approval, review, **Approve**; approve Ananya's ramp-up plan; **"Reduce
   key-person risk"**: add a backup for work only Tara does (the next resignation is cheaper).
6. **As Ananya:** same question, cited answer: "from Nisha, approved by Aditi", with the graph path;
   "Ask how" on a ramp-up item.
7. **As Aditi (close):** "Reduce key-person risk" now lists Ananya as the only person on all of
   Nisha's work. The handover moved the risk; it did not remove it. Add a backup, and the next
   resignation is cheaper. This is the "before anyone resigns" pitch.

Each switch shows a different person seeing different things, enforced by the graph. The readiness
checks are one definition (`app/backend/services/readiness.py`) used by the handover page and the
HR overview; each viewer gets actions only for the checks they can act on.

**Backups are active employees only**: a joiner cannot cover anyone before
their first day. Joiners receive work through the approved transfer and the ramp-up plan instead.

**Approval does not end the handover**. Managers often approve on the
successor's first day while the leaver is still answering. Anything the leaver confirms after the
approval appears as "New since approval" on the Transfer tab, in readiness ("N new since approval")
and in Needs attention; the manager approves it as a follow-up transfer (knowledge only, same
lineage). A transferred handover stays in everyone's context: the successor keeps "Your first 30
days", the leaver can still answer, and a ramp-up plan created after the approval is built from what
the leaver held just before it.

### 10.6 Out of scope for the hackathon

Real login, email/Slack notifications (in-app badges only), an admin console, separate executive or
IT apps. Keycloak is an architecture slide ([identity-and-access.md](identity-and-access.md)).

## 11. Successor ramp-up plan

Answer to ServiceNow's onboarding ramp-up plan:
theirs comes from a course catalogue; ours comes from the predecessor's actual work in the graph.

**Agent design: the graph decides what, the LLM only words it.**

1. **Gather (graph queries only, no LLM).** For an open handover, candidate items with a link to
   their graph node:
   - accounts where the leaver is the only admin;
   - the leaver's recurring responsibilities with cadence and next due date;
   - contacts only the leaver works with, plus the manager and team;
   - decisions and procedures the successor inherits (or will inherit), especially those that
     justify a current setting.
2. **Arrange (rules).** Week 1: access, anything due within 7 days, decisions behind live
   settings. Week 2: introductions, shadowing recurring work. Weeks 3–4: owning recurring work,
   procedures to practise.
3. **Word.** One line per item on why it matters, from fixed templates over that item's graph
   data. (An LLM rewrite via Groq was tried and dropped because it echoed titles
   and added nothing the graph did not already say.)
4. **Store in the graph.** `(:RampPlan {id, status, created_at, approved_at})-[:FOR]->(successor)`,
   `(:RampPlan)-[:FROM]->(:Handover)`, `(:RampPlan)-[:HAS_ITEM]->(:RampItem {id, week, kind, title,
   why, due_at, done_at})-[:ABOUT]->(Responsibility|Account|Stakeholder|Knowledge)`. Visible in
   Graph X-ray.
5. **Approve and track.** Only the leaver's manager approves (may remove items or move them between
   weeks), same rule as transfers. The successor sees "Your first 30 days" on their home and ticks
   items off; progress ("6/14 done") shows on the successor and manager homes.

**Build list:** backend queries (`graph/queries/ramp_*.cypher`), `services/ramp.py` (gather,
arrange, word, store), endpoints (`GET/POST /api/handovers/{id}/ramp`, approve, tick) with rules in
`services/access.py`; frontend card on `pages/home/SuccessorHome.tsx` and a review card on
`pages/home/ManagerHome.tsx`; unit tests for arrange rules and access, a query test against the
seeded graph.
