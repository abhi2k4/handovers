# Graph Model: Schema, Memory, Time, Provenance, Data Boundaries

## 1. Design principles

1. **Three layers, never mixed.**
   - **Source** layer: immutable evidence (commits, PRs, tickets, incidents, meetings, messages,
     documents, interview answers). Append-only.
   - **Knowledge** layer: org-owned, shared, bi-temporal claims, decisions and procedures.
     Never deleted; superseded or retracted instead.
   - **Memory** layer: agent-owned. A `Memory` node means "this agent holds this knowledge/event",
     with its own confidence, acquisition path and lineage. Transfers create *new memories*, not
     copies of knowledge.
2. **Nothing is overwritten.** Updates become new nodes plus `SUPERSEDES`. Retractions set
   `retracted_at`. Deletion only happens for GDPR-style erasure (out of scope; see §7).
3. **One FalkorDB graph per tenant.** FalkorDB is natively multi-graph: every query targets exactly
   one graph key, so a single Cypher query cannot cross tenants.
4. **Time is stored as integer epoch milliseconds.** FalkorDB supports temporal types, but its docs
   list *temporal arithmetic functions* as unsupported
   ([cypher-support](https://docs.falkordb.com/cypher/cypher-support)). Integers are
   range-indexable, compare reliably, and serialise cleanly. The API renders ISO-8601.
   Open-ended intervals use the sentinel **`253402300799000`** (9999-12-31T23:59:59Z) instead of
   `null`, so "currently valid" stays a plain range predicate that can use an index.
5. **Stable string ids** (`emp:alex`, `svc:recon`, `clm:recon.retry_limit@2024-06-12`). Never use
   FalkorDB internal `id()`, which the docs say is not immutable.
6. **Multi-labels for families.** Every evidence node also carries `:Source`, and every knowledge
   node also carries `:Knowledge`. Queries can then say `(s:Source)` or `(k:Knowledge)`, because
   FalkorDB does not support label expressions such as `:A|B`
   ([cypher-support](https://docs.falkordb.com/cypher/cypher-support)).
   *Verify multi-label CREATE/MATCH (checklist §9).*

### Concept consolidation (concept list → model)

| Requested type | Modelled as | Why |
|---|---|---|
| Fact | `Claim` (`:Knowledge:Claim`) | "Fact" implies truth; a claim carries confidence and validity |
| Knowledge | Family label `:Knowledge` on Claim/Decision/Procedure | Avoids a vague node that duplicates the others |
| Memory | `Memory` (agent-owned pointer + lineage) | Separates *who knows* from *what is known* |
| Conversation | `Session` + `Turn` | One concept; Session = conversation |
| System | `System` (external/third-party, e.g. the bank API) | Different from internally owned `Service` |
| Commit/PR/Ticket/Incident/Meeting/Document | `:Source:<Type>` | All are evidence; Incident/Meeting are also episodic events |

---

## 2. Common property conventions

| Group | Properties | Applies to |
|---|---|---|
| Identity | `id` (string, unique per label), `name`/`title` | all |
| Valid time | `valid_from`, `valid_to` (int ms; sentinel = open) | Knowledge, time-bounded relationships |
| Transaction time | `recorded_at`, `retracted_at` (int ms; sentinel = open) | Knowledge, Memory |
| Event time | `occurred_at` (int ms) | Source |
| Provenance | `origin` (`seed`/`ingest`/`interview`/`rule`/`transfer`/`human`), `origin_ref` (rule id, agent id, or connector id), `ingested_at` | all derived nodes |
| Classification | `sensitivity` ∈ `internal` < `team` < `restricted` < `personal` | Source, Knowledge, Memory |
| Lifecycle | `status` (per-type enum below) | Knowledge, Memory, Handover, Transfer, Gap |

Tenant scope for **every** node and relationship is its graph key `handover__<tenant_slug>`. There is
no per-node `tenant_id`. A single `(:Tenant)` node per graph holds tenant metadata.

---

## 3. Node types

### 3.1 Organisation

| Label | Key properties | Lifecycle / temporal | Owner |
|---|---|---|---|
| `Tenant` | `id`, `name`, `created_at`, `policy_version` | one per graph | platform |
| `Employee` | `id`, `name`, `email` (synthetic), `status` (`active`/`departing`/`departed`), `departed_at` | status transitions; never deleted | HR source |
| `Team` | `id`, `name` | stable | org |
| `Role` | `id`, `title`, `level` | stable | org |
| `Project` | `id`, `name`, `status`, `started_at`, `ended_at` | status | org |
| `Service` | `id`, `name`, `tier` (1–3), `repo_id` | stable | owning team |
| `System` | `id`, `name`, `vendor` | stable | – |
| `Repository` | `id`, `name`, `url` | stable | owning team |

### 3.2 Sources (`:Source:<Type>`, immutable)

Common: `id`, `system` (`github`/`jira`/`slack`/`docs`/`pager`/`calendar`/`handover`), `url`
(synthetic), `occurred_at`, `title`, `content` (short text), `sensitivity`, `quality`
(see §5.3), `ingested_at`.

| Label | Extra properties |
|---|---|
| `Commit` | `sha`, `message`, `files` (string array) |
| `PullRequest` | `number`, `state`, `merged_at` |
| `Ticket` | `key`, `type`, `status`, `resolved_at` |
| `Incident` | `key`, `severity`, `category`, `started_at`, `resolved_at` |
| `Meeting` | `kind` (`design_review`/`retro`/`1:1`), `notes` |
| `Message` | `channel`, `thread_id` |
| `Document` | `doc_type` (`adr`/`runbook`/`design`/`wiki`), `last_edited_at` |
| `InterviewAnswer` | `handover_id`, `gap_id`, `confirmed_by_author` (bool) |

### 3.3 Knowledge (`:Knowledge:<Type>`, bi-temporal)

Common: `id`, `statement` (one-sentence human text), `status`
(`proposed`/`confirmed`/`superseded`/`retracted`), `confidence` (derived, §5.3), `sensitivity`,
`visibility` (`org`/`team`/`holders`), `valid_from`, `valid_to`, `recorded_at`, `retracted_at`,
`origin`, `origin_ref`.

| Label | Extra properties | Notes |
|---|---|---|
| `Claim` | `subject_id`, `predicate`, `value`, `value_type` | Semantic memory. e.g. `svc:recon` · `retry_limit` · `"3"` |
| `Decision` | `title`, `rationale`, `decided_at`, `alternatives` (string array) | Semantic + episodic anchor |
| `Procedure` | `title`, `steps` (string array), `handles_category`, `version`, `last_verified_at` | Procedural memory |

### 3.4 Agent memory

| Label | Key properties | Lifecycle |
|---|---|---|
| `Agent` | `id`, `kind` (`personal`/`interview`/`orchestrator`), `status`, `created_at`, `initialized_from` (transfer ids, string array) | personal agent per employee; `status=retired` when its employee departs (memory retained, read-only) |
| `Memory` | `id`, `memory_type` (`episodic`/`semantic`/`procedural`), `acquired_via` (`observed`/`interview`/`transfer`/`conversation`), `acquired_at`, `confidence`, `status` (`active`/`revoked`/`archived`), `revoked_at`, `sensitivity`, `origin_agent_id`, `origin_memory_id`, `transfer_id`, `approval_id`, `note` (agent-private annotation) | create → (transfer) → revoke/archive; never deleted |
| `Session` | `id`, `started_at`, `ended_at`, `purpose` (`qa`/`interview`) | persists across process restarts (Track 02: memory across sessions) |
| `Turn` | `id`, `role` (`user`/`agent`), `text`, `at`, `answer_status` (`answered`/`abstained`) | append-only |

Connectors (app/backend/services/connector_config.py): a `Connector` node per connected account:
`id` (the platform id for its first account, `github:<slug>` for more), `platform`, `label`,
`config` (encrypted settings), `cursor`, `status`, `last_sync`, counts (`sources`, `facts`, `review`,
`people`), `active` (directories: one per category), `test_ok` / `test_message` / `tested_at`.
`(:Connector)-[:SERVES]->(:Team)` is the teams a work-tool account serves; records it syncs carry
`Source.origin` = its id.

Sign-in (app/backend/api/auth.py): a signed-in browser session is a `Session` with `hash` (SHA-256 of
the cookie token, never the token), `created_at`, `expires_at`, `id_token`, linked `FOR` to the
`Employee` or `Operator` who signed in; deleted on sign-out. `Operator` (`id`, `name`, `email`) is
the platform admin, the Handovers team account that configures an organisation: not an employee, so
it has no team, work or knowledge, only sessions (`graph/queries/operator_ensure.cypher`).

`origin_*`, `transfer_id`, `approval_id` are **denormalised** for fast filtering and UI. The source of
truth is always the edges in §4.4.

### 3.5 Handover workflow

| Label | Key properties | Lifecycle |
|---|---|---|
| `Handover` | `id`, `trigger` (`departure`/`internal_move`/`leave_cover`/`rotation`), `status` (see [handover-rules.md](handover-rules.md); `cancelled` with `cancelled_at`, `cancelled_by`, `cancel_reason`), `effective_at`, `created_at`, `policy_version`, `error`, `letter_sent_at`, `letter_sent_by` | state machine; the leaver stays `active` after the transfer until `effective_at` |
| `Responsibility` | `id`, `kind` (`ownership`/`on_call`/`project`/`authorship`), `score` | per handover |
| `Gap` | `id`, `rule` (`G1`…`G9`; `M` asked of every leaver by policy; `Q` added by HR or the manager, `context` = the question it follows), `asked_by`, `dismissed_by`, `resolution` (`reassigned`, or the reason it was dropped), `target_id`, `seed_question`, `question`, `priority`, `status` (`open`/`answered`/`dismissed`) | per handover; unique on `(handover_id, rule, target_id)` |
| `Approval` | `id`, `decision` (`approved`/`rejected`), `scope` (`batch`/`item`), `comment`, `at` | immutable |
| `Transfer` | `id`, `status` (`planned`/`applied`/`revoked`/`failed`), `planned_at`, `applied_at`, `revoked_at`, `policy_version`, `counts` (string JSON) | state machine |
| `Policy` | `id` (`policy:org`), `version`, `rules_json` (withdrawal window, mandatory questions, HR teams and groups, leadership titles, group → role, time zone, country code, digest hour), `updated_by`, `updated_at` | versioned on every save ([handover-rules.md](handover-rules.md)) |
| `Job` | `id`, `key` (idempotency), `kind` (`digest`/`lastday`/`release_held`/`depart`/`letter`), `status` (`queued`/`running`/`done`/`failed`/`cancelled`), `run_at`, `attempts`, `payload` (string JSON), `handover`, `result`, `last_error` | the background job queue (`services/jobs.py`) |
| `Reassignment` | `id`, `status` (`proposed`/`approved`/`rejected`/`replaced`/`withdrawn`), `proposed_by`, `proposed_at`, `decided_by`, `decided_at`, `note` | an account handover the manager or IT proposed, waiting for HR |
| `Note` | `id`, `kind` (`note`/`confirmation`), `text`, `by`, `by_name`, `at` | HR's (or the approver's) notes on a handover; append-only |
| `AuditEvent` | `id`, `type`, `at`, `payload` (string JSON) | append-only |
| `Alert` | `id`, `kind` (`resignation`/`reminder`/`approval`/`lastday`/`candidate`/`digest`), `to`, `at`, `status` (`sent`/`app`/`held`/`digest`/`failed`), `title`, `body`, `buttons` (string JSON), `href`, `step`, `acted`, `acted_at` | append-only except `acted` |
| `ClearanceItem` | `id`, `key` (`admin:`/`access:`/`work:` + target, or `asset:`/`finance:`), `label`, `group`, `owner`, `target`, `ord`, `status` (`open`/`done`/`confirmed`), `by`, `updated_at` | per handover; `admin:` and `work:` rows read as confirmed once someone else holds the account or the work |
| `Candidate` | `id`, `name`, `phone`, `city`, `summary`, `source`, `must_met`, `must_total`, `verdicts` (string JSON), `created_at` | per vacancy; per-criterion verdicts, no overall score |
| `Channel` | `id` (`whatsapp`, `email`), `config` (encrypted Meta or SMTP settings), `enabled` (the master switch), `updated_by`, `updated_at` | one per delivery channel; set by the platform admin (Integrations → Alerts); `.env` is the fallback |
| `AlertSettings` | `employee`, `phone`, `email` (false = no email alerts; default on), `modes` (string JSON: kind → `instant`/`digest`/`off`), `quiet_from`, `quiet_to` (hours in the policy's time zone; both WhatsApp and email wait) | one per person; the WhatsApp opt-in record |

---

## 4. Relationships

Time-bounded relationships carry `valid_from`/`valid_to`. Derived relationships carry `origin`,
`origin_ref`, `recorded_at`.

### 4.1 Organisation

| Type | From → To | Properties | Semantics |
|---|---|---|---|
| `MEMBER_OF` | Employee → Team | valid_from, valid_to | membership history |
| `HAS_ROLE` | Employee → Role | valid_from, valid_to | role history |
| `REPORTS_TO` | Employee → Employee | valid_from, valid_to | management line (manager access) |
| `OWNS` | Employee/Team → Service | valid_from, valid_to, `kind` (`primary`/`secondary`) | ownership history |
| `ON_CALL_FOR` | Employee → Service | valid_from, valid_to | rotation |
| `WORKS_ON` | Employee → Project | valid_from, valid_to | – |
| `CHANGES` | Project → Service | – | project scope |
| `DEPENDS_ON` | Service → Service/System | – | blast radius |
| `IMPLEMENTS` | Repository → Service | – | – |
| `REQUIRES_KNOWLEDGE_OF` | Role → Service | `level` | successor requirements |
| `HAS_AGENT` | Employee → Agent | created_at | identity binding (1:1 for personal) |

### 4.2 Sources

| Type | From → To | Properties |
|---|---|---|
| `AUTHORED_BY` | Source → Employee | – |
| `IN_REPO` | Commit/PullRequest → Repository | – |
| `CONTAINS` | PullRequest → Commit | – |
| `REFERENCES` | Source → Source | – (PR → ticket, message → incident) |
| `CONCERNS` | Source → Service/Project/System | – |
| `RESPONDED_TO` | Employee → Incident | `role` (`commander`/`resolver`/`observer`) |
| `ATTENDED` | Employee → Meeting | – |

### 4.3 Knowledge

| Type | From → To | Properties | Semantics |
|---|---|---|---|
| `ABOUT` | Knowledge → Service/Project/System/Team | – | what the knowledge concerns |
| `EVIDENCED_BY` | Knowledge → Source | `kind` (`states`/`implies`/`rationale`), recorded_at | **provenance** |
| `JUSTIFIED_BY` | Claim/Procedure → Decision | recorded_at, origin | the "why" |
| `MOTIVATED_BY` | Decision → Source (Incident/Meeting/…) | – | triggering event |
| `DECIDED_BY` | Decision → Employee | – | accountability |
| `DOCUMENTED_IN` | Knowledge → Source:Document | – | durable documentation exists |
| `SUPERSEDES` | Knowledge → Knowledge | `at` | newer replaces older (older gets `valid_to = at`, `status = superseded`) |
| `CONTRADICTS` | Knowledge → Knowledge | `detected_at`, `origin_ref` (rule G6) | unresolved conflict |

### 4.4 Memory and lineage

| Type | From → To | Properties | Semantics |
|---|---|---|---|
| `HOLDS` | Agent → Memory | – | ownership of memory |
| `OF` | Memory → Knowledge or Source | – | what is remembered (Source = episodic) |
| `LEARNED_FROM` | Memory → Source/Session | – | how the *original* holder acquired it |
| `DERIVED_FROM` | Memory → Memory | `transfer_id`, `at` | **inheritance lineage** |
| `VIA` | Memory → Transfer | – | which transfer created it |
| `APPROVED_IN` | Memory/Transfer → Approval | – | governance |
| `HAD_SESSION` | Agent → Session | – | – |
| `HAS_TURN` | Session → Turn | `seq` | – |
| `USED` | Turn → Memory | `rank` | answer provenance |

### 4.5 Workflow and audit

| Type | From → To | Properties |
|---|---|---|
| `FOR` | Handover → Employee | departing person |
| `FOR` | Session → Employee or Operator | who a sign-in session belongs to |
| `SUCCESSOR` | Handover → Employee | – |
| `INITIATED_BY` | Handover → Employee | – |
| `HAS_RESPONSIBILITY` | Handover → Responsibility | – |
| `ON` | Responsibility → Service/Project | – |
| `AT_RISK` | Handover → Knowledge | `score`, `remaining_holders` |
| `HAS_GAP` | Handover → Gap | – |
| `TARGETS` | Gap → Knowledge/Service | – |
| `RESOLVED_BY` | Gap → InterviewAnswer | – |
| `HAS_TRANSFER` | Handover → Transfer | – | one or more: the first moves knowledge, work and relationships; each follow-up moves only knowledge captured after the previous approval |
| `FROM_AGENT` / `TO_AGENT` | Transfer → Agent | – |
| `INCLUDED` | Transfer → Memory (origin) | `score`, `reason` |
| `EXCLUDED` | Transfer → Memory (origin) | `reason` (`sensitivity`/`out_of_scope`/`low_confidence`/`retracted`/`rejected`) |
| `BY` | Approval → Employee | – |
| `GOVERNED_BY` | Transfer → Policy | – |
| `RECORDED` | AuditEvent → any | – |
| `ACTOR` | AuditEvent → Employee/Agent | – |
| `CLEARS` | Handover → ClearanceItem | – |
| `HAS_CANDIDATE` | Handover → Candidate | – |
| `ABOUT` | Alert → Handover | – |
| `SENT_TO` | Alert → Employee | – |
| `WANTS_ALERTS` | Employee → AlertSettings | – |
| `CONFIRMS` | Decision → Knowledge | `at`: the leaver named this claim as current ("sources disagree") |
| `RESOLVES` | Decision → Knowledge | `at`: the claim that answer closed; both claims stay |
| `HAS_REASSIGNMENT` | Handover → Reassignment | – |
| `OF` / `TO` | Reassignment → Account / Employee | which account, to whom |
| `HAS_NOTE` | Handover → Note | – |

---

## 5. Memory model (J)

### 5.1 Memory kinds

| Kind | Question | Representation |
|---|---|---|
| Episodic | What happened? | `Memory -[:OF]-> (:Source:Incident\|Meeting\|PullRequest…)`, `occurred_at` |
| Semantic | What is true? | `Memory -[:OF]-> (:Claim\|:Decision)` |
| Procedural | How do we do it? | `Memory -[:OF]-> (:Procedure)` with ordered `steps` |
| Temporal | When was it true? | `valid_from`/`valid_to` on Knowledge; `SUPERSEDES` chain |
| Provenance | Where did it come from? | `EVIDENCED_BY` → Source → `AUTHORED_BY` |
| Confidence | How well supported? | `Knowledge.confidence` (§5.3); `Memory.confidence` defaults to it |
| Uncertainty | What don't we know? | `Gap` nodes; `status='proposed'` claims |
| Conflicts | What disagrees? | `CONTRADICTS` + Gap G6 |
| Supersession | What replaced it? | `SUPERSEDES` |
| Transfer lineage | Where did this memory originate? | `DERIVED_FROM*` chain → root memory → `LEARNED_FROM` |

### 5.2 Lifecycle operations

| Operation | Effect (all writes also create an `AuditEvent`) |
|---|---|
| create | New Source (ingest) or Knowledge (seed/interview); `MERGE` on `id` (idempotent) |
| extract | Interview answer → proposed Claim/Decision/Procedure + `EVIDENCED_BY` the answer (LLM proposes, human confirms) |
| merge | Same `(subject_id, predicate, value)` with overlapping validity → add `EVIDENCED_BY` to existing claim; no duplicate |
| update | Never in place for meaning-bearing fields. A new value means a new node + `SUPERSEDES`. Cosmetic fields (`statement` wording) may be edited, and an audit event records the old value |
| supersede | `old.valid_to = new.valid_from`, `old.status='superseded'`, `(new)-[:SUPERSEDES {at}]->(old)` |
| invalidate | Was never true: `retracted_at = now`, `status='retracted'`; memories pointing to it are flagged in retrieval |
| retrieve | Always agent-scoped (§7), always time-filtered (as-of default = now) |
| transfer | `services/handover.py`: approved items get `KNOWS` edges for the successor |
| approve | `Approval` node + `APPROVED_IN` edges |
| revoke | `Memory.status='revoked'`, `revoked_at`; `Transfer.status='revoked'` when all its memories are revoked |
| audit | Read `AuditEvent`s and lineage edges |

### 5.3 Confidence (deterministic, explainable)

Each Source has a `quality` prior assigned by type. These are design constants and get tuned only
against the benchmark:

| Source type | quality |
|---|---|
| Document (ADR/runbook), confirmed interview answer | 0.85 |
| Merged PR, commit | 0.80 |
| Incident record | 0.75 |
| Ticket | 0.65 |
| Meeting notes | 0.60 |
| Chat message | 0.50 |
| Unconfirmed interview answer | 0.40 |

`Knowledge.confidence = 1 − Π(1 − quality_i)` over **distinct** supporting sources (noisy-OR),
capped at 0.99. Recomputed by one query whenever `EVIDENCED_BY` changes. A claim backed by one chat
message scores 0.50 (weak). A PR plus an ADR scores 0.97.

---

## 6. Temporal reasoning (N)

Bi-temporal: **valid time** (`valid_from`/`valid_to`, when it was true in the world) and
**transaction time** (`recorded_at`/`retracted_at`, when the system believed it). Same idea as
Graphiti/Zep's `valid_at`/`invalid_at`/`created_at`/`expired_at`
([Zep facts](https://help.getzep.com/facts)).

| Question | Pattern |
|---|---|
| What is true now? | `k.valid_from <= $now AND $now < k.valid_to AND k.retracted_at > $now` |
| What was true in 2024? (point in time `$t`) | `k.valid_from <= $t AND $t < k.valid_to AND k.recorded_at <= $now AND k.retracted_at > $now` |
| What did we *believe* on date `$b` about time `$t`? | add `k.recorded_at <= $b AND k.retracted_at > $b` |
| Why did it change? | `(new)-[:SUPERSEDES]->(old)`, `(new)-[:JUSTIFIED_BY]->(d:Decision)-[:MOTIVATED_BY]->(e)` |
| Who made the decision? | `(d)-[:DECIDED_BY]->(e:Employee)` |
| What replaced it? | `(new)-[:SUPERSEDES]->(old {id:$id})` |

`$now` is passed in by the application (not `timestamp()` inside the query). The benchmark can
then pin "now", so temporal tests stay deterministic.

---

## 7. Provenance (O) and data boundaries (P)

### 7.1 Provenance chain for an answer

```
(:Turn)-[:USED]->(m:Memory)<-[:HOLDS]-(sarahAgent)
   (m)-[:VIA]->(:Transfer)-[:APPROVED_IN]->(:Approval)-[:BY]->(priya)
   (m)-[:DERIVED_FROM]->(m0:Memory)<-[:HOLDS]-(alexAgent)<-[:HAS_AGENT]-(alex)
   (m0)-[:OF]->(c:Claim)-[:JUSTIFIED_BY]->(d:Decision)-[:MOTIVATED_BY]->(inc:Incident)
   (c)-[:EVIDENCED_BY]->(pr:PullRequest)  (d)-[:EVIDENCED_BY]->(ans:InterviewAnswer)
```

UI display (Successor chat, right panel):

1. **Answer** with inline citation chips `[DEC-…] [INC-2291] [PR #418] [Interview]`.
2. **"Why you know this"** card: *Inherited from Alex Rivera's agent · Transfer T-… · approved by
   Priya Nair on 2026-10-17 · originally learned from PR #418 and interview answer.*
3. **Path graph** (Cytoscape.js): nodes coloured by layer (Source / Knowledge / Memory / Workflow),
   time chips on Knowledge nodes, superseded nodes greyed out.
4. **As-of** label: "true from 2024-06-12 to present".
5. **Raw** toggle: the Cypher query and its parameters, so the answer can be checked by hand.

### 7.2 Data boundaries (hackathon-sized security model)

| Boundary | Enforcement |
|---|---|
| Tenant isolation | Graph key per tenant, chosen only from the server-side request context; no API accepts a graph name |
| Agent memory isolation | Every Q&A/tool query is anchored at `(:Agent {id:$agent_id})-[:HOLDS]->(m:Memory {status:'active'})`. Knowledge is reachable only through own memories, plus `visibility='org'` knowledge |
| Read-only tools | Agent tools run through `GRAPH.RO_QUERY` (FalkorDB rejects writes there, [docs](https://docs.falkordb.com/commands/graph.ro-query)); only application services write |
| Successor access | Gains memories only through an applied, approved `Transfer` |
| Manager access | May view handover analysis for direct reports (`REPORTS_TO` valid now); cannot read `personal` memories |
| Source permissions | `Source.sensitivity`; `personal` sources are never projected or shown to others |
| Memory classification | `Memory.sensitivity = max(knowledge.sensitivity, source.sensitivity)` |
| Consent | Employee review step is mandatory; items marked private become `EXCLUDED {reason:'employee_private'}` |
| Transfer approval | `restricted` items require item-level approval; others may be batch-approved |
| Audit trail | `AuditEvent` on every state change; lineage edges are themselves the audit of knowledge movement |
| Revocation | Sets `Memory.status='revoked'`; retrieval filters it immediately; lineage is retained |
| Authentication | Out of scope. Demo identities are selected in the UI and sent as a header; documented as non-production |

---

## 8. Index and constraint plan

Bootstrap runs once per tenant graph (implemented as a versioned migration script
in `graph/`):

| Kind | Target |
|---|---|
| Range index (exact match) | `id` on every label; `Employee.status`; `Memory.status`; `Knowledge`: `predicate`, `subject_id`, `valid_from`, `valid_to`; `Source.occurred_at`; `Handover.status`; `Gap.rule` |
| Unique constraint (`GRAPH.CONSTRAINT CREATE … UNIQUE`) | `id` per label. FalkorDB requires the exact-match index **before** the constraint ([docs](https://docs.falkordb.com/commands/graph.constraint-create)) |
| Mandatory constraint | `id` on all labels; `valid_from`, `valid_to` on Knowledge |
| Full-text index | `Knowledge`: `statement`, `title`, `rationale`; `Source`: `title`, `content` |
| Vector index (stretch) | `Knowledge.embedding` via `CREATE VECTOR INDEX … OPTIONS {dimension, similarityFunction:'cosine'}` |

Known FalkorDB behaviours we design around
([known limitations](https://docs.falkordb.com/cypher/known-limitations)):

- Indexes are not used for `<>` filters, so we use positive status sets (`IN [...]`).
- When counting relationships matched in a pattern, the relationship alias must be referenced (e.g.
  in `RETURN count(r)`), otherwise counts can collapse.
- `LIMIT` does not limit eager writes. Write queries select their exact batch first.
- No aggregation inside pattern comprehensions. Aggregate in `WITH`.
- No regex operator. Use `STARTS WITH`/`CONTAINS`.

---

## 9. Verification checklist (run against the FalkorDB image in use)

- [ ] Multi-label nodes: `CREATE (:Source:Incident {id:'x'})`, then `MATCH (s:Source)` and `MATCH (i:Incident)` both return it.
- [ ] Range index on a label used by `MATCH (k:Knowledge)` is chosen in `GRAPH.EXPLAIN` when a node has multiple labels.
- [ ] Unique constraint on `id` per label rejects duplicates.
- [ ] Negative pattern predicate `WHERE NOT (c)-[:JUSTIFIED_BY]->(:Decision)` returns expected rows.
- [ ] `algo.betweenness({nodeLabels:[…], relationshipTypes:[…], samplingSeed: 42})` is stable across runs.
- [ ] `shortestPath` between resolved endpoints with typed relationships.
- [ ] Full-text `CALL db.idx.fulltext.queryNodes('Knowledge', $q) YIELD node, score` (confirm the yielded fields).
- [ ] `FalkorDBSaver` (langchain-falkordb) works with the LangGraph version we pin.
- [ ] Write throughput: single-graph concurrent writers from the async client (measure; claim nothing in advance).
