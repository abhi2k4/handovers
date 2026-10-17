# Data connectors

Handovers learns from the tools a company already uses. One connector per kind of tool:

| Kind | Platform | What becomes graph data | Status |
|---|---|---|---|
| Directory | Microsoft Entra ID | Employees, titles, departments, managers (disabled account = departed); Microsoft sign-in | Built |
| Directory | Google Workspace | Employees, titles, departments, managers (suspended or archived = departed); Google sign-in | Built |
| Chat | Slack | Threads and substantial messages, by author, with repliers | Built |
| Code | GitHub | Commits by author (merge commits skipped), pull requests with reviewers, issues by assignee | Built, verified on a live repo |
| Tickets | Jira Cloud | Issues by assignee, open or closed | Built |
| Docs | Notion | Pages by creator; runbooks and decision records typed from the title | Built |
| CRM | HubSpot | Contacts as stakeholders owned by their rep; deals as notes | Built |
| CRM | Salesforce | Contacts as stakeholders owned by their rep; opportunities as notes | Built |
| HR | OrangeHRM (open source) | Employees, managers, joiners and leavers | Planned (API access to verify) |

All connectors are tested against recorded API responses (`tests/unit/test_connector*.py`,
`tests/integration/test_connectors.py`); none has run against a live account yet. Verify each one with
a real free-tier account before the demo.

## How it works

- **Same path as an upload.** A connector (`app/backend/connectors/`) reads its platform's API and
  returns `SourceIn` evidence and, for directory and HR systems, people. It never writes to the graph.
  `app/backend/services/sync.py` extracts facts from the text (LLM or rules), then writes through the
  same review gate as uploads: confident facts about a known person go in, the rest wait in the
  review queue.
- **People are matched by email or name** (`ingestion/pipeline.py`, `Resolver`). Directory and HR
  connectors create or update employees by email and set who reports to whom.
- **Incremental.** Each connector returns a cursor (usually the newest timestamp it saw). The next sync
  starts there. A failed sync keeps the old cursor and is retried in full.
- **State lives in FalkorDB** as a `(:Connector {id, status, cursor, last_sync, sources, facts,
  review, people, error})` node (`graph/queries/connector_*.cypher`).
- **Who can run it:** HR and IT (`access.can_manage_connectors`). `GET /api/connectors` lists every
  connector, whether it is configured, the settings it needs (names only) and its last sync.
  `POST /api/connectors/{id}/sync` runs one.
- **Credentials are entered in the app:** HR or IT opens **Integrations → Connect**, fills in the
  form (each connector declares its fields, labels and hints) and saves. Values are encrypted with
  Fernet (key derived from `APP_SECRET_KEY`) and stored on the `Connector` node; secrets come back
  only as `••••1234`, and a blank secret on save keeps the stored one (`services/connector_config.py`).
  **Test connection** checks the form's values with one read-only call per platform (who the token
  signs in as, and that each repo, channel or project is readable) without saving anything; each
  connector's `check()` does it. The same settings in `.env` still work as a fallback; values from the app win. Rotating
  `APP_SECRET_KEY` makes stored values unreadable, so they have to be entered again.
- Secrets never reach the browser in full, the graph in plain text, or a log line. Errors name the
  host and HTTP status only.

For the hackathon, connectors use tokens created in each platform's free tier. A one-click OAuth
"Connect" per platform needs an app registration and a public callback URL per platform; it comes
after the event.

## Set up each platform

### GitHub

1. GitHub → Settings → Developer settings → **Fine-grained personal access tokens** → Generate new
   token.
2. Repository access: only the repositories to sync. Permissions, all **Read-only**: **Contents**
   (commits), **Issues** and **Pull requests** (Metadata is added automatically).
3. In `.env`: `GITHUB_TOKEN=<token>` and `GITHUB_REPOS=owner/repo,owner/other-repo`.
4. Or skip `.env`: **Integrations → GitHub → Connect**, paste the token and repositories, **Connect and sync**.

Each commit becomes a `Commit` source by its author (the first sync reads the newest 100 per repo;
later syncs only what is new), each pull request a `PullRequest` with reviewers as attendees, each
issue a `Ticket` by assignee. People are matched to employees by commit email, profile name or
login. Facts about someone who is not an employee wait in the review queue.

### Microsoft Entra ID (user directory and Microsoft sign-in)

Run this one first: it creates the people every other connector attributes work to. The same three
values also sign people in with Microsoft (`identity/microsoft_entra/`), so they are entered once.

1. Microsoft Entra admin center → **App registrations** → New registration (single tenant). Under
   **Authentication** add a **Web** redirect URI: the one Integrations → Sign-in → Microsoft Entra ID
   copies (`<KEYCLOAK_PUBLIC_URL>/realms/handovers/broker/microsoft/endpoint`, locally
   `http://localhost:8180/realms/handovers/broker/microsoft/endpoint`).
2. **API permissions** → Add → Microsoft Graph → **Application permissions** → `User.Read.All` →
   **Grant admin consent**.
3. **Certificates & secrets** → New client secret; copy the **Value**.
4. Integrations → Microsoft Entra ID → **Connect**: Directory (tenant) ID and Application (client) ID
   (both on the app's Overview page) and the client secret. Test connection, then Connect and sync.
   Sign-in uses the same values: "Continue with Microsoft", pinned to this tenant, so other Microsoft
   accounts cannot sign in. It turns on by itself when no other sign-in is active; otherwise use
   **Make active** on the Sign-in tab. (Or set `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`,
   `ENTRA_CLIENT_SECRET` in `.env` and press **Make active** there.)

A free Entra ID tenant is enough (the Microsoft 365 Developer Program sandbox comes with sample
users). People are matched to existing employees by email; new ones are created with their department
as team. Who reports to whom follows the directory.

### Google Workspace (user directory and Google sign-in)

The alternative to Entra for a company on Google. Reads people through the Admin SDK Directory API
([users.list](https://developers.google.com/workspace/admin/directory/reference/rest/v1/users/list));
the same card turns on "Continue with Google", pinned to the domain (Keycloak's Google provider with
`hostedDomain`: a personal Gmail or another company's account is refused).

1. [Google Cloud Console](https://console.cloud.google.com/): pick or create a project and enable the
   **Admin SDK API**.
2. **IAM & Admin → Service accounts** → create one (no roles needed) → **Keys → Add key → JSON**.
   Note its **client ID** (the number on its details page).
3. [Admin console](https://admin.google.com/) → **Security → Access and data control → API controls →
   Manage domain-wide delegation** → Add new: that client ID, scope
   `https://www.googleapis.com/auth/admin.directory.user.readonly` (read-only).
4. For sign-in: **APIs & Services → OAuth consent screen** (Internal), then **Credentials → Create
   credentials → OAuth client ID → Web application**, with the redirect URI that Integrations →
   Sign-in → Google Workspace copies (locally
   `http://localhost:8180/realms/handovers/broker/google/endpoint`).
5. Integrations → Google Workspace → **Connect**: the domain, an admin's email (directory reads act as
   them; Google requires an admin), the JSON key (paste the whole file), and the OAuth client ID and
   secret. Test connection, then Connect and sync. Google sign-in turns on by itself when no other
   sign-in is active; otherwise use **Make active** on the Sign-in tab. (Or set the `GOOGLE_*`
   values in `.env` and press **Make active** there.) If Entra is the active directory, this card
   is stored as inactive until you press **Make active** on it.

A [Google Workspace trial](https://workspace.google.com/) is enough to try it. Titles, departments
and managers come from each user's primary organization and manager relation.

### Slack

1. api.slack.com/apps → **Create New App** → From scratch → pick the workspace.
2. **OAuth & Permissions** → Bot Token Scopes: `channels:history`, `channels:read`, `users:read`,
   `users:read.email` → **Install to Workspace** → copy the Bot User OAuth Token (`xoxb-...`).
3. In each channel to sync: `/invite @<app name>`. The channel id is under channel details.
4. In `.env`: `SLACK_BOT_TOKEN=xoxb-...` and `SLACK_CHANNELS=C0123,C0456`.

Threads become one source each (the opening message plus replies); standalone messages under 40
characters are skipped.

### Jira Cloud

1. id.atlassian.com → Security → **API tokens** → Create API token.
2. In `.env`: `JIRA_BASE_URL=https://<site>.atlassian.net`, `JIRA_EMAIL=<the account's email>`,
   `JIRA_API_TOKEN=<token>`, `JIRA_PROJECTS=PAY,GROW` (project keys).

The free plan (up to 10 users) is enough.

### Notion

1. notion.so/my-integrations → **New integration** → Internal. Capabilities: Read content, and
   Read user information including email addresses.
2. Copy the Internal Integration Secret into `NOTION_TOKEN`.
3. Share each page or teamspace with it: page menu → **Connections** → add the integration.

Titles containing "runbook", "ADR", "decision", "SOP" or "job description" set the document type,
which the gap rules use (a written runbook is documentation; a fix only in tickets is not).

### HubSpot

1. HubSpot → Settings → Integrations → **Private apps** (newer accounts: Development → Legacy apps
   → Create private app).
2. Scopes: `crm.objects.contacts.read`, `crm.objects.deals.read`, `crm.objects.owners.read`.
3. Copy the access token into `HUBSPOT_TOKEN`.

The free CRM is enough. Each contact becomes a stakeholder owned by its HubSpot owner, written
straight to the graph (the CRM's owner field is authoritative, not an inference).

### Salesforce

1. Sign up for a free **Developer Edition** org.
2. For the demo, the Salesforce CLI gives a token: `sf org login web`, then `sf org display`
   shows the Instance Url and Access Token. These tokens expire after a few hours; a Connected App
   with the client-credentials flow is the long-term route.
3. In `.env`: `SALESFORCE_INSTANCE_URL` and `SALESFORCE_TOKEN`.

### OrangeHRM

Planned: OrangeHRM 5 (open source, runs in Docker) holds employees, managers and resignation
dates. A resignation there should open a handover here automatically. Its API access setup still
needs verifying on a running instance before we build it.

## Coming soon

`PLANNED` in `connectors/__init__.py` (and in `identity/__init__.py` for sign-in) lists platforms the
Integrations page shows as "coming soon": OrangeHRM, Confluence, Google Drive, Linear, GitLab, Zendesk;
Okta and Auth0 for sign-in.
Every sign-in provider is backed by a directory card (Entra, Google Workspace), so a provider is
entered once and the people who can sign in are the people the directory lists. Building one moves it from `PLANNED` to `REGISTRY`.

### Several accounts per work tool

A company rarely has one GitHub or one Jira. Each work tool can be connected **more than once**:
Integrations → Work tools → the platform's card → **Add account**. Each account has its own name
("Sales Jira"), credentials (encrypted), sync cursor and state, Test result, and the **teams it
serves**.

- The first account's id is the platform id (`github`), so a platform connected once is exactly as
  before; further accounts are `github:<slug>` (`POST /api/connectors/{platform}/accounts`). Every
  other route (`config`, `test`, `sync`, `DELETE config`) takes an account id.
- **Teams are for attribution, not access.** `(:Connector)-[:SERVES]->(:Team)`, and every record a
  sync writes has `Source.origin` = the account id, so "which team's tool did this come from" is a
  graph hop. Who can see what is still decided per person (`services/access.py`).
- Server `.env` values apply to the first account only; a further account never inherits them.
- Disconnecting a further account removes it; disconnecting the first clears its settings, name and
  teams. Synced records stay (knowledge is never deleted).
- Directories stay one account each (see below).

### One active provider per category

The directory and sign-in each have **one active provider at a time**, chosen independently:

| Category | Providers | Active means | Switching |
|---|---|---|---|
| Directory | Microsoft Entra ID, Google Workspace | The only directory that syncs people (`Connector.active`) | **Make active** on the other card: one write makes it active and the previous one inactive (`connector_activate`) |
| Sign-in | Sign in with Microsoft, Sign in with Google | The only provider on in Keycloak, so the login page offers one | **Make active** on the Sign-in tab: it is turned on and the previous one turned off, not deleted |

- **Settings are kept** when a provider becomes inactive, so switching back needs no re-entry;
  Keycloak also keeps people's links to a turned-off provider.
- **The first one connected becomes active.** Saving a second directory card stores it as inactive;
  its sign-in stays off while another is on. Saving the active one's card refreshes its sign-in.
- **Only the active directory syncs:** `POST /api/connectors/{id}/sync` on an inactive one answers
  409. **Deactivate** leaves no directory (or no sign-in) active. Disconnecting a card clears its
  settings, makes it inactive and removes its sign-in.
- **Test** on a connected card checks the saved settings and keeps the result (time, OK or the
  error) on the card until the settings change.
- Enforced in the backend (`services/connector_config.py`, `services/identity.py`, `services/sync.py`);
  the screens only explain it and ask before switching.

## Adding a connector

1. Add the settings to `core/config.py` and `.env.example`.
2. Add a package `connectors/<platform>/`: `connector.py` holds a `Connector` subclass (`id`, `name`,
   `category`, `fields`, `check()`, `pull()`), and `__init__.py` exports it. Call the platform with
   `get_json()` / `post_json()` from `connectors/http.py` so errors never include a credential.
   Shared mapping goes beside the packages (CRMs share `connectors/crm.py`).
3. Register it in `connectors/__init__.py`.
4. Add a unit test with recorded responses (`httpx.MockTransport`; no network in CI) and a section to
   this file.
