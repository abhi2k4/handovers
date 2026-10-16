# app/backend/connectors/

Data connectors: one package per platform, all behind one contract (`base.py`). A connector reads
a platform's API and returns `SourceIn` evidence and, for directories, people. It never writes to
the graph; `services/sync.py` does, through the review gate.

| Path | What |
|---|---|
| `base.py` | The contract: `Connector` (`id`, `name`, `category`, `fields`, `check()`, `pull()`), `Field`, `Pull`, `Person`, `ConnectorError` |
| `http.py` | `get_json` / `post_json`: errors an admin can read, never a credential |
| `crm.py` | What both CRMs produce: contacts as stakeholder facts, deals as notes |
| `__init__.py` | `REGISTRY` (what the Integrations page lists) and `PLANNED` (coming soon) |

| Package | Category | Reads |
|---|---|---|
| `entra/` | directory | Microsoft Graph users and managers; the same values sign people in with Microsoft |
| `google_workspace/` | directory | Admin SDK users (service account, domain-wide delegation); the same card signs people in with Google |
| `github/` | code | Commits, pull requests with reviewers, issues |
| `slack/` | chat | Threads and substantial messages |
| `jira/` | tickets | Issues by assignee |
| `notion/` | docs | Pages; runbooks and decision records typed from the title |
| `hubspot/`, `salesforce/` | crm | Contacts and deals by owner |

Work tools can have **several accounts** (a sales Jira and an engineering one), each with its own
credentials, sync state and the teams it serves ([how](../../../docs/connectors.md#several-accounts-per-work-tool)).
Directories are **one active at a time** (`connector_config.EXCLUSIVE`): only the active one
syncs, and switching keeps the other's settings ([rule](../../../docs/connectors.md#one-active-provider-per-category)).

Each package is `connector.py` (the class) plus an `__init__.py` that exports it. Adding a
platform: [docs/connectors.md](../../../docs/connectors.md#adding-a-connector).
