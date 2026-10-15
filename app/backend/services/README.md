# app/backend/services/

The product's logic. Services take a `Graph` (and an `LLM` when they generate text) and return
plain data; routers in `api/` call them. Pure rules stay free of I/O so they are unit-tested.

| Module | What |
|---|---|
| `access.py` | Every permission rule: roles (platform admin, HR, IT, manager, exec, employee) plus relationships |
| `policy.py` | Pure: gap weights, interview question templates, cadence maths, transfer rules |
| `analysis.py` | Read models: a person's work memory, org risk, handover gaps |
| `dashboard.py` | The landing view: what could walk out the door |
| `handover.py` | The handover workflow: open, analyse, interview, approve, transfer |
| `generators.py` | The four outputs for hiring a replacement: job description, screening criteria, résumé check, interview kit |
| `readiness.py` | Pure: what still blocks the last day, who owns it, the next action |
| `ramp.py` | The successor's ramp-up plan |
| `companion.py` | Answers from the leaver's memory, with sources, or says it does not know |
| `copilot.py` | The search bar: the app guide plus the caller's own memory |
| `kpis.py` | KPIs for the Insights page |
| `sync.py` | Run a connector: pull, extract, write through the review gate |
| `connector_config.py` | Connector credentials entered in the app: encrypted, masked on the way out |
| `identity.py` | Keycloak in step with the graph: people, the platform admin, sign-in providers |
| `alerts.py` | Who hears about what, how and when: in-app inbox, WhatsApp, quiet hours, digest |
| `whatsapp.py` | Sends through the Meta WhatsApp Cloud API (interactive, or a template outside the 24-hour window) |
| `clearance.py` | Exit clearance (no-dues): every account, piece of work and asset signed off before the letter |
| `candidates.py` | Candidates from a job board's CSV export (WorkIndia), screened per criterion |
| `delivery.py` | The alert channels the platform admin sets up (Integrations → Alerts): WhatsApp and email, encrypted settings over `.env`, a master switch per channel |
| `email.py` | Sends alert emails over SMTP (standard library; Mailpit in development) |
| `tech_graph.py` | The project graph behind "How it's built" ([graph/project/](../../../graph/project/README.md)) |
