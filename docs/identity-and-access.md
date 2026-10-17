# Identity and Access: Research and Proposal

Status: **phase 1 built**, see §0. The rest is research and proposal; re-verify versions
before building. Round 2 findings are in §9. Product roles and what each one sees
are defined in [product-strategy.md §4](product-strategy.md#4-users-and-roles).

## 0. What is built

Modelled on the kenz-intent backend (Backend-for-Frontend):

- **Keycloak 26.3** in Docker Compose behind the `auth` profile (`docker compose --profile auth up
  -d keycloak`), realm `handovers` imported from `deployment/keycloak/handovers-realm.json` on first
  start: one confidential client `handovers-backend` (authorization code + PKCE S256, service
  account allowed to manage users and identity providers). No people in the file.
- **Sign-in** (`core/keycloak.py`, `api/auth.py`): `/api/auth/login` sends the browser to Keycloak
  (straight to Google or Microsoft with `kc_idp_hint`); `/api/auth/callback` exchanges the code
  server-to-server, verifies the ID token against Keycloak's published keys (issuer, audience,
  expiry, nonce) and opens a session. The browser holds only an `httpOnly` cookie; the graph stores
  its SHA-256 hash (`Session` node). The sign-in attempt rides in a short-lived encrypted cookie.
  Sign-out ends every session of the person and Keycloak's own.
- **Nobody is created by signing in.** The email must belong to an active employee in the graph;
  the graph is the directory (seeded, or synced from Entra ID). `POST /api/auth/provision` ("Sync
  people" on Integrations) gives every employee a Keycloak account and disables people who left.
- **Sign-in providers are plug and play** (`identity/`, modelled on kenz-intent): one package per
  provider implementing `IdentityProvider` (`identity/base.py`), registered in `identity/__init__.py`;
  `services/identity.py` registers them in Keycloak through its admin API.
  - **Microsoft Entra ID** signs in with the Entra connector's tenant ID, client ID and secret
    (entered once, on Integrations), as an OpenID Connect provider pinned to that tenant.
  - **One sign-in provider is active at a time** (and, separately, one directory): making one
    active turns the other off in Keycloak, keeping its settings. Details and the full rule:
    [connectors.md](connectors.md#one-active-provider-per-category).
  - **Google Workspace** signs in with the Google Workspace connector's OAuth client, pinned to its
    domain (`hostedDomain`); the same card reads the directory with a service account
    (domain-wide delegation, read-only). See docs/connectors.md.
  - Each shows the redirect URI to register. Okta and Auth0 are listed as coming soon.
- **Guest mode stays:** with `ALLOW_GUEST=true` (the live link for judges) visitors can still
  explore as the demo personas; a signed-in session always wins over the View-as header, so nobody
  signed in can act as someone else. With `ALLOW_GUEST=false` everything requires sign-in.
- **Local demo only:** `DEMO_USER_PASSWORD` gives every employee that password in Keycloak, so the
  personas can sign in with email. Leave it empty anywhere real.

Not built yet: SCIM provisioning, roles from the directory, back-channel logout, a branded Keycloak
theme (email sign-in shows Keycloak's stock page; Google and Microsoft skip it).

---

> **Decision: open source only.** No paid services or SaaS subscriptions; community
> support is acceptable. Paid options below (WorkOS, unified HRIS APIs) are recorded for context only
> and are **out of scope**.

## 0a. Roles

Who uses Handovers once it is installed for an organisation. Rules live in `services/access.py`.

| Role | Who | Can | Cannot |
|---|---|---|---|
| **Platform admin** | The Handovers team, when we install it for an org | Integrations, sign-in providers, sync people, reload sample data | See people, handovers or any knowledge (not an employee) |
| **HR** | The org's HR team | Run handovers for anyone, org readiness, assign backups, add exit-interview questions, approve account handovers, confirm clearance, send the relieving letter, edit the company policy | Read interview answers or knowledge content; approve transfers (except as the last fallback, when no manager in the chain is staying) |
| **IT** | The org's IT team | Hand over a leaver's accounts and access | |
| **Manager** | Anyone with direct reports | Run their team's handovers, approve or send back transfers, propose account handovers, read their reports' answers, drop a question that does not apply | Approve when they are leaving too (the next manager up does) |
| **Exec** | Leadership | The leadership home and Insights (risk, handovers, outcomes), read-only | Change anything; open handover workspaces |
| **Employee** | Everyone in the directory | Their own home, memory and privacy settings | See other people's work |

*Leaver* and *successor* are stages of a handover, not roles.

Where roles come from:

- **Platform admin:** one account, `PLATFORM_ADMIN_EMAIL` with `PLATFORM_ADMIN_PASSWORD` (generated
  by `setup.py`), created in Keycloak at startup. It signs in with email and password and becomes an
  `Operator` node (not an `Employee`), so it has no home, team or knowledge; it lands on
  Integrations and sees only that. In guest mode, "View as" offers it as "Platform admin" so judges
  can open Integrations.
- **HR, IT, Exec:** from the company's policy (`services/org_policy.py`, edited under Policies): HR
  by team id, department name synced from the directory, or sign-in group; IT and leadership by
  group or job-title words. See [handover-rules.md](handover-rules.md).
- **Approver:** one per leaver: the manager, else the next one up who is staying, else HR
  (`access.pick_approver`).
- **Manager:** derived from reporting lines.

## 0b. Secrets

No secrets manager for the hackathon (kenz-intent's optional Infisical adds four containers; not
worth it here). Three places, each with one job:

| Secret | Lives in | Notes |
|---|---|---|
| Server secrets (FalkorDB password, `APP_SECRET_KEY`, Keycloak client secret and admin password, demo and platform admin passwords) | `.env`, generated by `python setup.py`, never committed | Production: the VM's own secret store fills `.env`; never baked into an image |
| Connector credentials (tokens, keys, client secrets entered in Integrations) | The graph, encrypted with Fernet under `APP_SECRET_KEY` (`core/security.py`) | Shown masked only. **Changing `APP_SECRET_KEY` makes them unreadable: re-enter them** |
| Sign-in client secrets (Entra, Google Workspace OAuth) | Keycloak's identity-provider config, through its admin API | Never returned to the browser |

## 1. Goal

**Plug and play.** A company keeps its users, groups and policies where they already live (Microsoft
Entra ID, Okta, Google Workspace, on-prem Active Directory). Handovers never becomes a second place
to manage people. An admin connects the company directory once; sign-in, users, groups and
de-provisioning then follow the directory automatically.

**Proposal (from the project lead):** self-hosted **Keycloak** sits between customer directories and
Handovers. Customer users and groups are brought into Keycloak, and Handovers trusts only Keycloak.

**Verdict: sound, with three refinements** (§6): use the standard sync protocol (SCIM) rather than
custom scripts, keep the HRIS as the source of org facts, and do relationship-based authorisation
in the graph rather than putting everything into roles.

## 2. What Keycloak offers today (verified)

| Capability | What it does | Status | Source |
|---|---|---|---|
| **Identity brokering** (OIDC/SAML) | Users sign in with their company IdP (e.g. Entra ID); Keycloak creates or updates the user on login. **Mappers** turn incoming claims into Keycloak roles or attributes (e.g. *Claim to Role*: Entra group object ID → Keycloak role) | Long-standing | [Server Admin Guide](https://www.keycloak.org/docs/latest/server_admin/), [SUSE: Entra ID via Keycloak](https://documentation.suse.com/cloudnative/suse-observability/latest/en/suse-cloud-observability/keycloak-sso/microsoft-entra-id.html) |
| **SCIM 2.0 API** (inbound) | IdPs *push* users and groups into a realm: CRUD and PATCH, filtering, paging, Enterprise User extension. Endpoint `/realms/{realm}/scim/v2`, opt-in per realm. Inbound only | **Supported** since **26.8.0** (preview in 26.7) | [Release notes](https://www.keycloak.org/docs/latest/release_notes/index.html), [Skycloak: 26.8 SCIM](https://skycloak.io/blog/keycloak-26-8-scim-api-supported/) |
| SCIM authentication | The caller uses OAuth 2.0 **client credentials** against Keycloak (confidential client, service account with the SCIM / manage-users roles) and sends the token as a bearer | 26.8 | [golinuxcloud: Keycloak SCIM API](https://www.golinuxcloud.com/keycloak-scim-api/) *(secondary source; confirm role names in the official guide)* |
| **LDAP / Active Directory federation** | Keycloak reads users (and groups, via mappers) from on-prem AD/LDAP with periodic sync | Long-standing | [Server Admin Guide](https://www.keycloak.org/docs/latest/server_admin/) |
| **Organizations** | Multi-tenancy inside one realm: members, an IdP linked per organization, email-domain routing; 26.8 adds IdPs shared across organizations | GA since 26 | [Release notes](https://www.keycloak.org/docs/latest/release_notes/index.html), [Red Hat: Managing organizations](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.0/html/server_administration_guide/managing_organizations) |
| Latest version | 26.8.0 (released 1 Oct 2026) | – | [Keycloak releases](https://github.com/keycloak/keycloak/releases) |

What the directories offer:

| Fact | Detail | Source |
|---|---|---|
| Entra ID provisions to custom SCIM apps | "Non-gallery application"; auth via long-lived bearer token, **OAuth 2.0 client credentials to a third-party token endpoint**, or workload identity federation; incremental sync **about every 40 minutes**; removed users are **disabled** (`active=false`) | [Microsoft: Develop a SCIM endpoint](https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups) |
| Entra group claims in tokens are capped | 200 groups in a JWT, 150 in SAML; above that the `groups` claim is replaced by an "overage" marker and the app must call Microsoft Graph. Microsoft recommends **app roles** (assign groups to app roles; token carries `roles`) | [Microsoft: group claims and app roles](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles) |
| Entra SCIM default attribute mapping | Users: `mailNickname → externalId` (Microsoft notes it may be missing or non-unique), `userPrincipalName → userName`, `employeeId → enterprise:employeeNumber`, `manager → enterprise:manager`. Groups: `objectId → externalId`. Mappings are editable | [Microsoft: Develop a SCIM endpoint](https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups) |
| Okta | Private SCIM integrations for custom apps, with header (bearer) or OAuth authentication | [Okta: Add a private SCIM integration](https://developer.okta.com/docs/guides/scim-provisioning-integration-connect/main/) |
| Google Workspace | **No generic outbound SCIM to custom apps**: automatic provisioning is limited to apps in Google's catalog (and users only, no groups, for some) *(secondary sources; confirm with Google's admin docs before promising)* | [AWS: Google Workspace with IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/gs-gwp.html), [Keeper: Google Workspace provisioning](https://docs.keeper.io/enterprise-guide/user-and-team-provisioning/google-g-suite-scim) |

## 3. Why both sign-in *and* sync are needed

Login-time brokering alone is not enough for Handovers. **We must know people who have never logged
in**: the leaver's manager, the successor before day one, every employee whose memory accrues.
So users and groups must be **pushed** (SCIM) or **pulled** (LDAP), not only created on first login.

| Path | Users exist before login | Groups stay current | De-provisioning | Use for |
|---|---|---|---|---|
| A. Brokering only (JIT) | ✗ | Only at login; 200-group cap on Entra | ✗ (until next login) | Sign-in, always |
| **B. SCIM push from the IdP** | ✓ | ✓ (~40 min on Entra) | ✓ (`active=false`) | **Default for cloud directories** |
| C. LDAP federation | ✓ | ✓ (scheduled sync) | ✓ | On-prem Active Directory |
| D. Custom script (Graph API → Keycloak Admin API) | ✓ (when it runs) | Until the next run | Only if the script handles deletes | One-time backfill or reconciliation only |

**Recommendation: A + B** for cloud directories, **A + C** for on-prem AD. D is a tool, not the
architecture: custom scripts drift, miss deletions, and need a privileged secret per customer. SCIM
is the standard Entra ID and Okta already speak.

## 4. Proposed architecture

```
Customer IdP (Entra ID / Okta / AD)
   │  OIDC sign-in (brokering)          SCIM push: users, groups, enterprise attrs (manager, dept)
   ▼                                     │
┌───────────────────────── Keycloak 26.8 (self-hosted) ─────────────────────────┐
│ realm per customer: handovers-<tenant>                                         │
│   identity provider: company IdP     SCIM API on     mappers: group → app role │
│   client: handovers-web (OIDC)        client: scim-ingest (service account)    │
└────────────────────────────────────────────────────────────────────────────────┘
   │ OIDC tokens (sub, email, tenant=realm, roles)       │ admin/user API (read users & groups)
   ▼                                                     ▼
Handovers backend ── verifies JWT (realm JWKS) ── tenant = realm → graph handovers__<tenant>
   │                                             caller = (:Employee) matched by stable id
   ▼
Authorisation = coarse role (from IdP groups) + relationship in the graph (manager-of, leaver, successor)
```

**Tenancy: one Keycloak realm per customer**, mirroring one FalkorDB graph per customer. Reasons:
the native SCIM endpoint and IdP configuration are per realm; isolation is simple to explain to a
security reviewer; deleting a customer deletes a realm and a graph. Keycloak Organizations (one
realm, many tenants) is the alternative if we reach hundreds of customers; revisit then.

**Keycloak needs its own database** (PostgreSQL). It holds identity configuration only; all product
data stays in FalkorDB, so the "FalkorDB is the primary database" rule is unaffected.

## 5. Authorisation model: roles are not enough

Most Handovers permissions are **relationships**, not roles: "manager *of this leaver*", "successor
*of this handover*", "the leaver *themself*". A directory group cannot express that; the graph can.

| Layer | Comes from | Examples | Evaluated |
|---|---|---|---|
| **App roles** (coarse) | Customer IdP groups → Keycloak roles (admin maps groups once) | `hr`, `recruiter`, `it`, `admin`, `exec`, default `employee` | From the token |
| **Relationships** (fine) | Graph edges synced from the HRIS / directory | `REPORTS_TO` (manager-of), `Handover-[:FOR]->` (leaver), `Handover-[:SUCCESSOR]->` (successor) | Per request, in Cypher |
| **Data classification** | Knowledge and source properties | `private`, `sensitivity`, transfer approval state | Inside every query |

Example policies (illustrative; the full matrix is in [product-strategy.md §4](product-strategy.md#4-users-and-roles)):

| Action | Allowed when |
|---|---|
| View a person's memory | caller is that person; or `manager-of` (non-private items only) |
| View handover workspace | role `hr`; or caller is the leaver's manager |
| Answer exit interview | caller is the handover's leaver |
| Approve transfer | caller is the leaver's manager (not HR alone) |
| Ask the companion | always; it only reaches the caller's own `KNOWS` edges (already true today) |
| See sole-admin accounts | role `it` or `hr`, or manager-of |
| Read audit log | role `admin` |

**Identity → graph link:** Entra's default `externalId` for users is `mailNickname`, which Microsoft
warns can be missing or non-unique. So the customer's Entra mapping should send the immutable
**object ID** as `externalId` (one change in the app's attribute mappings), and Entra already sends
**`employeeId` as `employeeNumber`**. Handovers links a Keycloak user to an `(:Employee)` by
`employeeNumber` (the HRIS key), then object ID, then work email, and reports anything unmatched.

**Directory vs HRIS:** the directory gives sign-in, groups and often `manager` and `department` (SCIM
Enterprise User extension). The **HRIS stays the source of truth** for role, team, notice period and
the resignation event. When they disagree, HRIS wins and we flag it.

## 6. Refinements to the proposal

1. **SCIM over scripts.** Entra ID and Okta push to Keycloak's native SCIM API (supported in 26.8).
   Scripts only for one-time backfill or reconciliation.
2. **App roles over raw groups** in Entra (avoids the 200-group overage; Microsoft's own
   recommendation). The customer admin assigns their groups to our roles once.
3. **ReBAC in the graph** for everything relationship-shaped; roles only for job functions.
4. **HRIS for org facts and triggers**; the directory for identity.
5. **Never trust identity from the UI or LLM tools.** Tenant and caller come only from the verified
   token (already an AGENTS.md rule).

## 7. "Single-click" customer onboarding (target UX)

1. Admin opens *Settings → Identity → Microsoft Entra ID*.
2. Handovers creates the customer realm, the OIDC client and the SCIM client, and shows: redirect
   URI, SCIM URL, token endpoint, client ID and secret.
3. Admin creates one Enterprise App in Entra (sign-in + provisioning), pastes those values and
   assigns groups to the app roles `hr`, `it`, `recruiter`, `admin`, `exec`.
4. First SCIM cycle imports users and groups; Handovers links them to employees from the HRIS and
   shows a reconciliation report (unmatched users, conflicts).
5. From then on: new hires appear, leavers are disabled, group changes apply within the sync cycle.

Steps 2 and 4 are automatable through the Keycloak Admin REST API; step 3 is the customer's one-time
work (Entra has no API we can call on their behalf without their consent).

## 8. Proposed phases (not started)

| Phase | Scope | When |
|---|---|---|
| H (hackathon) | Persona switcher with demo identities; the same policy table enforced in the API, so only the identity source changes later | Hackathon, if the team agrees |
| 1 | Keycloak (+ PostgreSQL) in Docker Compose; one realm; OIDC sign-in in the app; JWT verification in the backend | After the hackathon |
| 2 | SCIM from an Entra test tenant; employee linking and reconciliation report; role mapping UI | Pilot preparation |
| 3 | Realm provisioning automation (single-click flow), Okta, LDAP for on-prem AD, audit of every authorisation decision | First customers |

## 9. Research round 2

### Gaps the first draft missed

| Finding | Consequence |
|---|---|
| **Google Workspace cannot push SCIM to custom apps** (per secondary sources above) | For Google customers: OIDC sign-in through Keycloak brokering plus a **pull** of users and groups from the Google Admin SDK Directory API (customer grants read-only access), or rely on the HRIS for the people list. Keep this on the roadmap as a separate connector |
| Entra's default user `externalId` is not a safe key | Ask customers to map object ID to `externalId`; link employees by `employeeNumber` first (above) |
| The HRIS, not the directory, carries resignations and notice periods | Integrate HRIS through a **unified HRIS API** rather than one connector per vendor (below) |

### HRIS breadth: unified APIs

*Out of scope under the open-source-only decision; kept for context.* Our free path instead: a
**CSV/XLSX import of the HRIS employee export** (every HRIS can export one; the upload pipeline
already maps spreadsheets deterministically), plus direct connectors to the one or two HRIS APIs a
pilot customer actually uses, built on the customer's own API access.

Building one connector per HRIS (Workday, BambooHR, HiBob, Darwinbox, Keka, …) does not scale for a
small team. Unified HRIS APIs expose one schema for employees, employment status and managers across
many HRIS products, with change webhooks (built on their periodic syncs). Candidates:
[Merge](https://www.merge.dev/categories/hr-payroll-api), [Knit](https://getknit.dev/integration-categories/unified-hris-api/),
[Unified.to](https://docs.unified.to/hris/overview). Per-vendor coverage (notably Darwinbox and Keka
for India) and how quickly a termination shows up must be checked per provider before choosing; the
search results claim coverage but this is unverified.

### Fine-grained authorisation: graph-native, not a separate engine

Zanzibar-style engines ([OpenFGA, SpiceDB](https://www.osohq.com/learn/openfga-alternatives)) exist for
relationship-based access. We do not need one: FalkorDB already holds the relationships
(`REPORTS_TO`, `FOR`, `SUCCESSOR`, `KNOWS`), and every query already anchors at the caller. A second
store of relationships would be a second source of truth to keep in sync. Revisit only if
authorisation must be shared with other services.

### Build vs buy for identity

| Option | Fit | Cost / effort |
|---|---|---|
| **Keycloak, self-hosted** (proposed) | Open source; SSO + native SCIM (26.8) + LDAP; customers that require self-hosting or data residency are covered | Infrastructure plus operations: Keycloak's own sizing guide suggests about **2 GB** memory for small production containers and a **dedicated PostgreSQL**; load scales with logins and token refreshes, not total users ([Keycloak sizing](https://www.keycloak.org/high-availability/multi-cluster/concepts-memory-and-cpu-sizing)). Our current e2-medium VM would need to grow |
| WorkOS (managed SSO + Directory Sync) | Fastest to ship; webhook-based directory events | Per-connection pricing reported at about $125/month for SSO and the same again for directory sync per customer at low volume (secondary sources, e.g. [idsync](https://idsync.com/guides/workos-pricing)); vendor lock-in |
| Zitadel (open source) | Built multi-tenant first (organisations) | SCIM described as preview in comparisons; smaller ecosystem than Keycloak (secondary sources, e.g. [Keycloak vs Zitadel](https://skycloak.io/blog/keycloak-vs-zitadel-comparison/)) |

**Decision: Keycloak** (open source, mature, self-hostable, SCIM API now supported). WorkOS is paid and
therefore out of scope; Zitadel is the open-source fallback if Keycloak's operation becomes the
bottleneck.

## 10. Open questions

1. Realm per tenant vs Organizations: confirm when we expect more than ~100 customers.
2. Google Workspace customers: Directory API pull connector, or HRIS-only people list?
3. Do we also accept SCIM straight from HRIS systems that support it, or always go through the IdP?
4. Hosting Keycloak per region for data residency (EU, India).
5. Who can see what during an HR investigation (break-glass access), and how it is logged.
