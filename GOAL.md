# KAIRO — Master Project Goal & Anti-Hallucination Specification

> **Document Purpose:** Single Source of Truth (SSOT) for AI coding agents, developers, and reviewers.
> **Rule:** Every coding session MUST start by reading this file. Every task MUST be verified against this file before marking it complete.
> **Version:** 1.0 | **Status:** ENFORCED — Do NOT deviate without explicit human approval.

---

> [!CAUTION]
> This is the canonical goal document. If any code, design decision, database schema, API contract, or UI interaction contradicts what is written here, the code is WRONG — not this document. Stop, revert, and realign before proceeding.

---

## GOAL COMPLETION CHECKLIST (Check Before Every Commit & PR)

Before any task is considered "done", the AI agent or developer MUST verify each of the following:

- [ ] **G-01:** Desktop client is Tauri 2.0 (Rust + React). Not Electron. Not a web app. Not a browser extension.
- [ ] **G-02:** Company admin portal (Next.js 14) is ONLY for org registration, tool OAuth setup, and installer download. It is NOT a daily developer tool.
- [ ] **G-03:** Every database query (SQL or Cypher) filters strictly by `organization_id`. No exceptions.
- [ ] **G-04:** Every LLM-generated statement has an inline citation: `[PR:#]`, `[Commit:SHA]`, `[Jira:KEY]`, `[Slack:thread_id]`. Zero ungrounded claims.
- [ ] **G-05:** Anomaly detection (HW-01 to HW-05) is deterministic Python logic ONLY. LLM must never decide if work is anomalous.
- [ ] **G-06:** Permission checks use Pre-Retrieval ACL filter. Database returns 0 chunks for unauthorized repos before LLM is ever called.
- [ ] **G-07:** GitHub Teams permissions are auto-inherited — not manually configured by admins inside KAIRO.
- [ ] **G-08:** Team shift triggers: (a) old squad unfinished work alert + (b) new squad Welcome Briefing. Both automatic.
- [ ] **G-09:** Active task detection uses local `.git/HEAD` watcher (Rust). Not screen scraping. Not polling APIs.
- [ ] **G-10:** No surveillance features. No lines-of-code counts, no developer productivity rankings, no active working hours tracking. EVER.
- [ ] **G-11:** All docs in `docs/` are updated immediately when any backend mechanism, schema, or API changes.
- [ ] **G-12:** Backend test coverage stays at >= 85%. `anomaly_rules.py` requires 100% branch coverage.

---

## 1. What is KAIRO? (Non-Negotiable Core Identity)

**KAIRO is an enterprise AI-powered Work Continuity & Temporal Knowledge Engine.**

Its single, non-negotiable job is:
> **When a developer leaves a task, changes teams, or offboards — the incoming developer or team suffers ZERO context loss.**

KAIRO is NOT:
- A code review tool
- A project management tool (not replacing Jira/Linear)
- An employee monitoring/surveillance tool
- A GitHub analytics dashboard
- A standalone web app that developers must log into every day

KAIRO IS:
- A passive, always-on work continuity engine that lives silently in the developer's system
- A cited knowledge reconstruction engine that proves every claim with real code evidence
- A team transition orchestrator that detects unfinished, shadow, and anomalous work
- A security-first multi-tenant system where one company's data NEVER touches another's

---

## 2. The Business Problem Being Solved

When **Rahul** (Senior Dev) leaves task `PAY-421: Stripe Integration` and **Aman** takes over:

| Without KAIRO | With KAIRO |
| :--- | :--- |
| Aman spends 3-5 days reading old code | Aman gets a cited briefing in < 3 seconds |
| Hidden unlinked PRs/branches go undiscovered | Anomaly Radar flags all shadow work |
| Jira says "Done" but CI is failing | HW-03 Rule catches the mismatch deterministically |
| "Why did Rahul choose Redis?" is unknown | Decision lineage in Neo4j graph answers it with citation |
| Manager has no visibility into risk | "Single Point of Failure" map shows who owns what |

---

## 3. The 2-Piece System Architecture (FIXED — Do NOT Change)

```
PIECE 1: Company Web Portal  (apps/web)
Purpose: Admin ONLY — Org setup, tool OAuth, installer download. NO daily dev use.
Stack:   Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui

PIECE 2: Developer Desktop Floating HUD  (apps/desktop)
Purpose: Installed on every developer's machine. Always-on overlay. Zero context switching.
Stack:   Tauri 2.0 (Rust backend + React 18 + TypeScript frontend + Tailwind CSS)
```

Both pieces connect to one **FastAPI Backend** (`apps/api`).

---

## 4. Complete User Journey (Per Persona — Fixed Reference)

### 4.1. Company Admin / CTO (One-Time, Day 0)

1. Signs up at `app.kairo.dev` with Google/Okta SSO.
2. Tenant `organization_id` is created and cryptographically scoped.
3. Connects tools via 1-click OAuth:
   - GitHub App: selects repos to monitor
   - Jira Cloud: selects projects (e.g. `PAY`, `MEET`, `INFRA`)
   - Slack: selects alert channels
   - Google Drive / Taiga (optional)
4. Gets an installer download page and a secure team invite link with onboarding token.
5. Sends invite link to developers via email/Slack.
6. Background cold-start sync begins: past 30-90 days of PRs, commits, Jira tickets indexed into Postgres + Neo4j.

**Admin never returns to the portal for daily use.**

---

### 4.2. Developer / Employee (One-Time Setup, Then Passive Use)

**First-Time Setup (30 seconds):**
1. Downloads KAIRO Desktop installer from company invite link.
2. Opens app, clicks "Sign in with Company Google" (`@snapmeet.com`).
3. Tool Pairing Screen shows:
   - GitHub account linked (`@aman-v`) — verified via GitHub OAuth
   - Jira account linked (`aman_v`) — verified via Jira OAuth
   - Slack linked (`@aman`) — verified via Slack OAuth
4. App minimizes to a small floating pill in the top-right corner of the screen.

**Daily Workflow (Zero Friction — Developer changes NOTHING about their habits):**
- Developer works normally in VS Code, Cursor, Terminal.
- KAIRO Rust daemon silently watches `.git/HEAD` and `.git/config`.
- When developer switches to `feat/BILL-204-razorpay`, the HUD pill shows:
  `Active: SnapMeet / billing-service / BILL-204 (Razorpay Invoicing) [green indicator]`

**On Demand (1-Click or Keyboard Shortcut):**
- Developer clicks the pill or presses `Ctrl/Cmd+K`.
- Action Drawer slides open with:
  1. Quick Context (what the task is, what prior developer did)
  2. Anomaly alerts (unmerged PR, failing CI)
  3. Day-1 Action Checklist
  4. Grounded Q&A Chat (role-scoped to authorized repos only)

---

### 4.3. Incoming Developer After Handoff (Aman's Day 1)

**Trigger:** Jira assignee changed from Rahul to Aman on `BILL-204`.

**What Aman automatically receives:**
1. Slack DM from KAIRO Bot: "Hi Aman! BILL-204 has been handed over to you. [Open Handoff]"
2. Desktop HUD switches context to `BILL-204` automatically.
3. Handoff Drawer opens with:
   - Executive Briefing with mandatory `[PR:#]`, `[Commit:SHA]`, `[Jira:KEY]` citations on every claim
   - Anomaly Radar showing HW-01 to HW-05 alerts
   - Day-1 Checklist with 3 specific next steps
   - Grounded Q&A chat

**Aman cannot see** repos/tickets outside his authorized GitHub teams — enforced at database level.

---

### 4.4. Engineering Manager / Lead (Ongoing Visibility via Web Portal)

- **Team Continuity Map:** Which devs own which services. Single-point-of-failure alerts.
- **Active Anomaly Feed:** All HW-01..HW-05 alerts across the org in real-time.
- **Handoff History:** All completed and pending handoffs with timestamps and coverage scores.

---

## 5. Active Context Detection (Exactly How It Works — Do Not Change)

```
Step 1: Rust `notify` crate watches active workspace `.git/HEAD` file
        Changes on `git checkout <branch>` detected in < 1ms

Step 2: `.git/config` parsed for remote URL
        Extracts: repo = `snapmeet/billing-service`

Step 3: Branch name parsed via regex
        Pattern: ^(?:feat|fix|chore|refactor)/(?P<ticket>[A-Z]+-\d+)
        Extracts ticket: `BILL-204`

Step 4 (Fallback): If no ticket in branch name, query Jira API
        "What In-Progress ticket is assigned to Aman in repos matching billing-service?"
        Returns: `BILL-204`

Step 5: HUD pill updates context display
        "Active: SnapMeet / billing-service / BILL-204 [green]"
```

**NOT done via:** Screen scraping, keylogging, time tracking, or any surveillance mechanism.

---

## 6. Permission & Access Control (Exactly How It Works — Do Not Change)

### 6.1. How Permissions Are Set (Automatic — Zero Manual KAIRO Config)

1. Admin connects GitHub App on Day 0.
2. KAIRO calls `GET /orgs/{org}/teams/{slug}/repos` for each team.
3. Maps: `@aman-v` is in `@snapmeet/billing-team` which has access to `["billing-service", "auth-service"]`.
4. Stored in Supabase `user_repo_permissions` table with `organization_id` scoping.
5. Jira projects similarly inherited via `GET /rest/api/3/mypermissions`.
6. GitHub API response example: `{"permission": "none"}` for `executive-financials` — that repo is blocked.

### 6.2. How Permissions Are Enforced (Pre-Retrieval ACL — Security Gate)

```
Developer Query
     |
     v
FastAPI JWT Decode — extracts user_id and allowed_repos
     |
     v
Database query with STRICT filter:
  WHERE organization_id = :org_id
  AND repo_id IN (:allowed_repos)
     |
     +------ 0 chunks (blocked) -------> 403 Forbidden (LLM never invoked)
     |
     +------ chunks found -------------> LLM Synthesis with citation validation
```

### 6.3. Team Shift Update (Automatic Real-Time)

**Trigger:** GitHub fires `membership.added` + `membership.removed` webhook.

**KAIRO Actions (< 1 second):**
1. Old team repos removed from developer's allowlist.
2. New team repos added to developer's allowlist.
3. In-flight unmerged PRs in old repos flagged for reassignment.
4. New squad architecture context loaded in Desktop HUD.

**Fail-safe:** Nightly cron reconciles all permissions against live GitHub/Jira APIs.

---

## 7. Evidence Resolution Engine — 4 Tiers (Do Not Change)

| Tier | Method | Confidence | When Used |
| :--- | :--- | :--- | :--- |
| **T1: Structural IDs** | Regex on branch name + commit msg + GitHub linked issues metadata | 100% | `feat/BILL-204`, `Fixes #88`, PR linked to issue |
| **T2: Temporal Graph** | Persona canonicalization + active time-window + file module overlap in Neo4j | 95% | Vague commits ("wip", "fix") during active ticket window |
| **T3: Code AST Diff** | Tree-sitter AST: new functions, classes, API routes matching acceptance criteria | 90% | Feature code matching ticket description keywords |
| **T4: Vector Semantic** | pgvector 768-dim cosine similarity >= 0.82 on Slack/PR text | 85%+ | Unlinked Slack debates, vague commit messages |

> [!IMPORTANT]
> If none of the 4 tiers can link a commit to any ticket — it becomes a Shadow Work HW-01 alert. It is NEVER silently ignored.

---

## 8. Hidden-Work Anomaly Rules (HW-01 to HW-05)

All 5 rules are **pure deterministic Python boolean logic** in `apps/api/app/engines/anomaly_rules.py`.
The LLM NEVER determines whether an anomaly exists.

| Rule | Trigger Condition | Severity |
| :--- | :--- | :--- |
| **HW-01: Shadow Work** | Commit author == developer, but no linked Jira ticket found via T1..T4 | HIGH |
| **HW-02: Stalled Work** | PR inactive > 7 days with unresolved merge conflicts | MEDIUM |
| **HW-03: State Mismatch** | Jira status == `Done` BUT (PR state == `Open` OR CI == `Failed`) | HIGH |
| **HW-04: Architecture Drift** | Code imports a service that is absent from the architecture diagram graph | LOW |
| **HW-05: Orphaned Dependency** | Task depends on a service/module with `ActiveMaintainers == 0` | HIGH |

---

## 9. LLM Synthesis Rules (Non-Negotiable — Every LLM Call Site)

1. **No hallucination:** Every claim must map to a registered evidence ID in the evidence manifest.
2. **Injection-safe prompts:** Ingested content (commits, PR descriptions, Jira comments) goes into parameterized `packages/prompts/` template slots only. Never string-concatenated into system instructions.
3. **Pre-Retrieval ACL first:** ACL filter always runs before retrieval. LLM never sees unauthorized data.
4. **Output validation:** Structured LLM outputs validated against Pydantic v2 schema. Malformed responses fail the request — never coerced or guessed.
5. **Token budget:** Every LLM call site declares a `max_tokens` budget. No unbounded loops over commits or tickets.

---

## 10. Full Tech Stack (Fixed — Do NOT Substitute Without Explicit Human Approval)

| Layer | Technology | Exact Tools |
| :--- | :--- | :--- |
| **Desktop App** | Tauri 2.0 | Rust (`notify` crate, `tauri` v2) + React 18 + TypeScript + Tailwind CSS + Framer Motion |
| **Company Web Portal** | Next.js 14 | App Router + TypeScript + Tailwind CSS + shadcn/ui |
| **Backend API** | FastAPI | Python 3.11+ + Pydantic v2 + `uv` package manager (NOT pip) |
| **Task Queue** | Celery | Redis (Upstash cloud / local Docker) as broker |
| **Relational DB** | Supabase PostgreSQL 16 | `pgvector` for 768-dim embeddings. Alembic for migrations. |
| **Graph DB** | Neo4j AuraDB | Cypher queries. Parameterized ONLY — no f-string Cypher ever. |
| **LLM / Embeddings** | Google Gemini API | `text-embedding-004` (768-dim). Gemini 1.5/2.0 Flash for synthesis. |
| **Code Intelligence** | Tree-sitter | Python + TypeScript + Go grammar parsers for AST diffs |
| **CV Pipeline** | OpenCV + PaddleOCR | Architecture diagram bounding box + text extraction |
| **Auth** | Supabase Auth | Google OAuth / Okta SSO / GitHub OAuth |
| **Resilience** | Tenacity | Exponential backoff on ALL external API calls |
| **Python Linting** | Ruff + Mypy | Strict type checking enforced |
| **TS Linting** | ESLint + Prettier | Enforced in CI |
| **Testing** | Pytest | `pytest-asyncio`, `pytest-cov`. >= 85% coverage enforced in CI. |
| **DevOps** | Docker Compose | Full local stack: `docker compose up --build` |

> [!WARNING]
> Do NOT swap Tauri for Electron. Do NOT use `pip` instead of `uv`. Do NOT use Pydantic v1.
> These are architectural constraints — not preferences.

---

## 11. Repository Directory Structure (Fixed)

```
kairo/
├── apps/
│   ├── api/                        # FastAPI backend (Python 3.11+)
│   │   ├── app/
│   │   │   ├── api/                # REST routes + webhook ingress controllers
│   │   │   ├── core/               # Config (get_settings()), logging, errors, resilience
│   │   │   ├── engines/            # Anomaly rules (HW-01..05), reconstruction, state machines
│   │   │   └── services/           # Supabase, Neo4j, Redis, LLM, GitHub/Jira/Slack sync
│   │   └── tests/                  # Unit + integration + contract tests (>=85% coverage)
│   ├── desktop/                    # Tauri 2.0 Desktop Floating HUD (Rust + React)
│   └── web/                        # Next.js 14 Company Admin Portal ONLY
├── workers/
│   └── tasks/                      # Celery async workers (ingest, OCR, synthesis, team shift)
├── packages/
│   ├── schemas/                    # Shared Pydantic v2 models + TypeScript types
│   └── prompts/                    # Versioned injection-safe LLM prompt templates
├── db/                             # Supabase PostgreSQL DDL migrations + RLS policies
├── graph/                          # Neo4j Cypher schema, migrations, traversal queries
├── cv_pipeline/                    # OpenCV + PaddleOCR diagram parser
├── fixtures/                       # Seeded demo data (Rahul to Aman transfer scenario)
├── docs/                           # All architecture + API + security documentation
├── AGENTS.md                       # AI Agent rules and contributor guide (ENFORCED)
└── GOAL.md                         # THIS FILE — Master goal and anti-hallucination spec
```

---

## 12. Hard Prohibitions (AI Agent Must Never Violate)

| # | Prohibited Action | Reason |
| :--- | :--- | :--- |
| P-01 | Track lines of code per developer | Surveillance — ethics violation |
| P-02 | Rank developer productivity or velocity | Surveillance — ethics violation |
| P-03 | Track active working hours | Surveillance — ethics violation |
| P-04 | Query any data without `organization_id` filter | Tenant data leak |
| P-05 | Generate LLM output without inline citations | Hallucination shipped as fact |
| P-06 | Let LLM determine anomaly state (HW-01..05) | Non-deterministic, unreliable |
| P-07 | Run ACL filter after LLM retrieval | Security — data already seen by LLM |
| P-08 | Use Electron for the desktop app | 250MB RAM vs 15MB — defeats purpose |
| P-09 | Build a developer-facing daily web dashboard | Defeats zero-friction design goal |
| P-10 | Use f-string formatted Cypher or SQL queries | Injection vulnerability |
| P-11 | Hardcode secrets, API keys, or tokens anywhere | Critical security violation |
| P-12 | Disable CI checks or skip tests to merge | Quality gate bypass |

---

## 13. Documentation Maintenance Rule (Permanent — Every Task)

> [!IMPORTANT]
> Every time any of the following changes: backend mechanism, engine rule, data model, API contract, permission logic, UI interaction pattern, or tech stack decision — the AI agent MUST immediately update the relevant `docs/*.md` file AND this `GOAL.md` file.
>
> A code change without a corresponding doc update is an INCOMPLETE task per Definition of Done in `AGENTS.md`.

**Files that must stay synchronized at all times:**

- `GOAL.md` — this file, master goal and checklist
- `AGENTS.md` — AI agent operational rules and directory map
- `docs/01-architecture-and-system/overview.md` — system topology
- `docs/01-architecture-and-system/engines-and-algorithms.md` — HW rules and state machines
- `docs/01-architecture-and-system/evidence-resolution-and-verification.md` — 4-tier evidence engine
- `docs/01-architecture-and-system/desktop-overlay-and-access-control.md` — Desktop HUD and ACL
- `docs/02-integrations-and-connectors/*.md` — GitHub, Jira, Slack connector specs
- `docs/03-api-and-contracts/*.md` — REST endpoints and webhook contracts

---

## 14. The Canonical Demo Scenario (Single Ground Truth for All Testing)

All development, testing, and benchmarking must validate against this exact scenario:

**Company:** SnapMeet Inc. (100 employees, SaaS video platform)
**Outgoing Dev:** Rahul Sharma — GitHub: `@rahul-snap`, Jira: `rahul_s`, Slack: `@rahul`
**Incoming Dev:** Aman Verma — GitHub: `@aman-v`, Jira: `aman_v`, Slack: `@aman`
**Task:** `BILL-204: Razorpay Subscription & Webhook Invoicing` in repo `billing-service`
**Trigger Event:** Manager changes Jira assignee from Rahul to Aman

**8 Expected Outcomes (All Must Pass):**

1. KAIRO detects the Jira webhook trigger in < 1 second.
2. 4-Tier Evidence Engine reconstructs all relevant PRs, commits, branches, and Slack threads linked to `BILL-204`.
3. **HW-03 anomaly fires:** Jira `BILL-204` was marked "Done" but PR #88 is Open with failing CI checks.
4. **HW-01 anomaly fires:** Rahul had 2 unlinked commits in branch `rahul/temp-fix` with no associated Jira ticket.
5. Grounded cited Executive Briefing delivered to Aman's Desktop HUD in < 3 seconds.
6. Aman's Desktop HUD switches active context from whatever he was working on to `BILL-204`.
7. Aman asks Q&A: "Where is the webhook secret?" — KAIRO responds with cited answer referencing `config/settings.py:L34` and `[Commit e91c2b]`.
8. Aman queries about `executive-financials` repo — KAIRO returns 403 Access Restricted. LLM is never invoked.

> [!CAUTION]
> If ANY of these 8 outcomes fails or behaves differently from what is specified above, the implementation is incorrect and must not be merged.
