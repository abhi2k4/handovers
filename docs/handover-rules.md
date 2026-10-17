# Handover rules: the business-logic loopholes, closed

Status: **built**. Code: `app/backend/services/handover_rules.py` (pure rules),
`services/handover.py` (workflow), `services/access.py` (who may do what), `services/org_policy.py`
(the company's policy), `services/jobs.py` (background jobs), `services/letters.py` (relieving
letter). Tests: `tests/unit/test_handover_rules.py`, `test_org_policy.py`, `test_access.py`,
`tests/integration/test_handover_rules_flow.py`.

Each rule below names the loophole, the decision, and where it is enforced. The UI only offers
what the API allows; the API is the referee.

## The company's policy (`Policy` node)

Exits differ by company, so the rules that were hard-coded live in one versioned `Policy` node,
edited in the app (**Policies**, HR or the platform admin). Defaults describe the sample company.

| Setting | Default | Used for |
|---|---|---|
| `withdrawal_days` | 7 | How long after the resignation a handover can be cancelled |
| `letter_on_last_day` | true | The relieving letter is sent from the last day, not before |
| `mandatory_questions` | 4 questions | Asked of every leaver, never dismissable |
| `hr_teams` | `team:people`, "people", "human resources", "hr", … | Who is HR: a team id, a department name synced from the directory, or a sign-in group |
| `hr_is_it` | true | In small companies HR also administers accounts |
| `exec_titles` | ceo, founder, chief, managing director | Leadership, from job titles |
| `role_groups` | `{}` | Sign-in (SSO) group → `hr` / `it` / `exec` (reads `Employee.groups`) |
| `timezone` | Asia/Kolkata | Quiet hours, the daily digest, dates on letters |
| `country_code` | 91 | Local phone numbers typed without a prefix |
| `digest_hour` | 9 | When the daily summary job runs |

## The rules

| # | Loophole | Decision | Enforced in |
|---|---|---|---|
| 7 | Approving the transfer marked the leaver departed at once, locking them out weeks early | Approval moves knowledge, work and contacts; the leaver stays `active`, signs in and answers late questions until the last day. A `depart` job on `effective_at` marks them departed and ends every access they still hold (`leaver_access_end`, history kept). | `approve_and_transfer`, `depart`, job `depart` |
| 7b | Nothing used the days left | **Capture plan**: today to the last day, questions spread over all but the last two days, recurring work due before the last day done *together* with the successor, sole contacts introduced in the first third, accounts moved two days out, clearance on the last day. Once every required answer is in, it keeps going: extra questions, then walkthroughs of work only the leaver does. HR sees counts, not question content. | `handover_rules.capture_plan`, `GET /handovers/{id}/capture-plan` |
| 8 | Successor could be the leaver, someone leaving, or someone gone (and approval revived them) | Refused (`self`, `leaving`, `departed`). Another team is allowed after confirming (409 `{code: other_team, confirm: true}`, then `confirmed: true`). Checked again at approval. Approval only activates a successor who was `incoming`. | `handover_rules.successor_problem`, `check_successor` |
| 9 | The leaver could dismiss their own questions; HR could dismiss what it can't read | Only the leaver's manager (or the approver) drops a question, with a reason kept in the audit. Mandatory questions (rule `M`) can't be dropped. HR and the manager **add** questions and follow-ups (rule `Q`); the leaver is notified; they join the required set. Readiness waits on mandatory + asked + the top 8 found; the rest are "More to capture". | `access.can_dismiss_question`, `can_ask_question`, `handover_rules.interview_sets` |
| 10 | "Accounts reassigned" could be faked | Done only when someone else actually holds the admin in the graph (gap `resolution = reassigned`), never because the question was answered. Never to the leaver, or to someone leaving or gone. The leaver keeps access until the last day (`HAS_ACCESS.until = effective_at`). The manager or IT **proposes** (`Reassignment` node); HR approves and the account moves (HR's own reassignment applies at once). | `readiness.build`, `POST /handovers/{id}/accounts/{aid}/reassign`, `POST /reassignments/{id}/decide` |
| 11 | Resolving "sources disagree" always retired the older claim, whatever the answer said | The leaver picks which claim is current (pre-selected from what the answer says, e.g. "₹450 is current"). Both claims stay: the other is closed (`valid_to`, `status = superseded`), and the answer is its own decision node that `CONFIRMS` the kept claim and `RESOLVES` the closed one. "Neither" changes nothing. | `handover_rules.suggest_claim`, `confirm_answer`, `claim_resolve.cypher` |
| 12 | No way to cancel a handover | HR or the manager cancels with a reason within the policy's window (never after the transfer, never past the last day). Pending account proposals are withdrawn, queued jobs cancelled, the people involved told. | `handover_rules.cancel_window`, `POST /handovers/{id}/cancel` |
| 13 | Nobody could approve when the leaver had no manager, or the manager was leaving | One approver per leaver: the direct manager; if gone or leaving, the next manager up who is staying (up to 4 levels); else HR. The approver reads answers (HR still never does). | `access.pick_approver`, `approval_routes.cypher`, `Caller.approves` |
| 14 | Letter before the last day and visible to the leaver; HR could confirm clearance alone; a manager could undo HR | Clearance: the owner marks done, then HR confirms (two sign-offs, both recorded). Only HR changes a confirmed row. The approver approves **or sends back** with a reason. HR keeps notes and confirmations (`Note`, hidden from the leaver). The letter is drafted as an editable email once clearance and the transfer are done, sent from the last day (now, or scheduled as a `letter` job), and only then visible to the leaver. | `set_clearance`, `reject_transfer`, `letters.gate`, `POST /handovers/{id}/letter` |
| 15 | Reminders didn't run on their own; quiet hours held WhatsApp but not email | A job queue in FalkorDB (`Job` nodes) with an in-process worker (`JOBS_ENABLED`, `JOBS_POLL_SECONDS`): `digest` and `lastday` daily at the policy hour, `release_held` hourly, `depart` and `letter` per handover; up to 3 tries with backoff. Quiet hours now hold every channel; `release_held` sends WhatsApp and email together once they end. **Policies → Background jobs** lists the queue and runs a job now. | `services/jobs.py`, `services/notices.py`, `alerts.route` |
| 16 | Roles only worked for `team:people`; leadership guessed from titles; quiet hours and phones assumed India | Roles come from the policy: HR by team id, department name or sign-in group; IT and leadership by group or title; time zone and country code per company. | `org_policy.roles_for`, `access.hr_people` |

## Demo notes

- The sample company's clock is pinned (`DEMO_NOW`), so scheduled jobs never come due on their
  own. Use **Run now** on Policies → Background jobs.
- Nisha's handover opened 8 days ago with a 7-day window, so it can no longer be cancelled; start a
  new one (e.g. Kabir) to show cancellation.
- Pick Arjun (Engineering) as Kabir's successor to show the other-team confirmation.
