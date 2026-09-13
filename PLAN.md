# FinScA — Financial Services Agent (End-to-End Plan)

**Status:** Plan of record. Implementation progress lives in **[PROGRESS.md](PROGRESS.md)** — do not treat this file as the live tracker.

**Product:** A single-user, local-first **Agentic CLI** that turns bank-statement PDFs, Gmail, and SMS dumps into a monthly financial report: accounts + balances, labeled transactions, cash-flow intent, spend habits, EMIs, channel ratios, salary cycle, GST, and a financial-health score.

**Name:** FinScA (Financial Services Agent)

---

## 1. Locked assumptions

These are product decisions implied by the request. Implementation treats them as final unless overridden.

| Topic | Decision | Why |
|---|---|---|
| Audience | One human, on their own machine | “My finances”, CLI, local inbox/archive |
| Geography | India-first (INR, UPI, NEFT/IMPS/RTGS, DC/CC, GST, EMI) | Ratios and GST only make sense this way |
| UI | CLI only for v1 (Rich tables + ASCII/HTML graphs) | Agentic CLI, not a web app |
| Persistence | SQLite in `data/finsca.db` | Zero-ops, portable, enough for one household |
| Ingestion default | File drop into `data/inbox/` | Deterministic, reviewable, no always-on daemon |
| Gmail | File drop (`.eml` / `.mbox` / Takeout) in v1; optional Gmail API later | Avoid OAuth complexity blocking the first useful report |
| SMS | User-provided dump: XML (SMS Backup & Restore), CSV, or JSON | “SMS dump provided by the user” |
| LLM | Provider router: **Grok (xAI)** + **OpenAI** + a **compact** cheap model | Explicit request |
| Agent style | Orchestrator + many small subagents, structured I/O | No single god-file, no one giant ReAct loop for ingest |
| Currency | INR, amounts as `Decimal` paise-safe | Never float money |
| Privacy | Keys in `.env` (gitignored); raw statements never leave disk except as redacted LLM snippets | Bank PDFs are highly sensitive |

The two most expensive reversals are **live Gmail API in v1** and **multi-user/server**.

---

## 2. What “done” looks like

A user can:

1. Drop PDFs / email files / SMS dumps into `data/inbox/{pdf,email,sms}/`.
2. Run `finsca ingest` — parse, normalize, dedupe, detect self-transfers, auto-label, queue income-vs-transfer confirms, update monthly opening/closing balances, archive the inbox.
3. Run `finsca review` — confirm flagged credits as **Income** or **Transfer** (answers become reusable rules).
4. Run `finsca label` — change a category; the correction is remembered.
5. Run `finsca report --month 2026-08` — cash flow, habits, DC/CC/UPI mix, salary cycle, GST, health score, EMI book, ASCII + optional HTML graphs.
6. Run `finsca ask "why did dining jump in July?"` — orchestrator routes to the right subagent and answers from the ledger, not from vibes.
7. Inbox is empty after a successful run; originals live under `data/archive/<run-id>/`.

Self-transfers and paired legs **never count twice** in income, spend, or savings rate.

---

## 3. Architecture

### 3.1 Three runtimes, one codebase

```
┌─────────────────────────────────────────────────────────────┐
│  CLI (Typer + Rich)                                         │
│  finsca ingest | review | label | accounts | loans | report │
│  finsca ask "..."                                           │
└─────────────┬───────────────────────────────┬───────────────┘
              │ deterministic pipelines       │ conversational
              ▼                               ▼
┌──────────────────────────┐    ┌─────────────────────────────┐
│  Pipeline Orchestrator   │    │  Conversational Orchestrator│
│  (ingest / month close)  │    │  (ask / ad-hoc analysis)    │
└─────────────┬────────────┘    └──────────────┬──────────────┘
              │ calls                          │ routes
              ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│  Subagents (each: own module, tools, pydantic I/O, tests)   │
│  pdf · email · sms · normalize · label · confirm · ledger   │
│  cashflow · loans · health · archive · report               │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐
│ Domain       │  │ Repositories │  │ LLM Router              │
│ (pure)       │  │ (SQLite)     │  │ Grok | OpenAI | Compact │
└──────────────┘  └──────────────┘  └─────────────────────────┘
```

**Rule:** ingest is a **pipeline of subagents**, not a free-form chat. LLMs are used inside stages (parse unknown PDF, classify merchant, draft narrative). `finsca ask` is the only full tool-calling loop.

Bank math must not depend on a model “feeling” a balance.

### 3.2 Layering (no god-files)

| Layer | Allowed to know | Forbidden |
|---|---|---|
| `cli/` | Typer, Rich, calling orchestrators | SQL, PDF parsing, prompts |
| `agents/` | Tools, prompts, calling domain + repos + LLM | Typer, raw PDF bytes |
| `ingest/` | File formats, bank layouts | LLM client construction, CLI |
| `finance/` | Pure functions on domain objects | I/O, LLM, CLI |
| `db/` | SQLAlchemy, SQL | LLM, CLI, PDF |
| `llm/` | Providers, routing, token budgets | Domain rules, SQL |
| `core/` | Pydantic models, enums, money | Everything else |

If a file starts importing from three layers, it gets split.

### 3.3 Alternatives considered

1. **One ReAct agent with 40 tools** — faster to prototype, impossible to test, one bad tool call corrupts the ledger. Rejected.
2. **Airflow/Prefect + a chat wrapper** — overkill for a local CLI. Rejected for v1.
3. **Recommended: staged pipeline + thin conversational orchestrator.** Deterministic money path, LLM only where language or messy layout exists.

---

## 4. Python project structure

Package name: `finsca`. Python 3.11+. Hatchling via `pyproject.toml`. Entry point: `finsca = finsca.cli.app:app`.

This tree is the **target** layout. Workspace currently holds only data folders and this plan — source modules are created when implementation starts.

```
FinScA/
├── PLAN.md                        # this document
├── pyproject.toml                 # (implementation)
├── README.md
├── .env.example
├── .gitignore
├── data/                          # gitignored except .gitkeep
│   ├── inbox/pdf|email|sms/
│   ├── archive/
│   ├── reports/
│   └── finsca.db
├── src/finsca/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli/
│   │   ├── app.py                 # Typer root
│   │   ├── render.py              # shared Rich tables / prompts
│   │   └── commands/
│   │       ├── ingest.py
│   │       ├── review.py          # income vs transfer
│   │       ├── label.py
│   │       ├── accounts.py
│   │       ├── loans.py
│   │       ├── report.py
│   │       ├── ask.py
│   │       └── config_cmd.py
│   ├── config/
│   │   ├── settings.py            # pydantic-settings from env + ~/.finsca.toml
│   │   ├── labels.yaml            # default category taxonomy
│   │   └── banks.yaml             # bank id, last4 hints, statement quirks
│   ├── core/
│   │   ├── enums.py               # AccountType, Channel, Intent, SourceKind
│   │   ├── money.py               # Decimal INR helpers
│   │   ├── ids.py                 # ulid / content hashes
│   │   └── models.py              # Pydantic domain DTOs only
│   ├── db/
│   │   ├── engine.py
│   │   ├── session.py
│   │   ├── schema.py              # SQLAlchemy tables
│   │   └── repositories/
│   │       ├── accounts.py
│   │       ├── transactions.py
│   │       ├── labels.py
│   │       ├── loans.py
│   │       ├── rules.py
│   │       └── ingest_runs.py
│   ├── llm/
│   │   ├── types.py
│   │   ├── router.py              # picks grok | openai | compact by task
│   │   ├── openai_provider.py
│   │   ├── grok_provider.py
│   │   ├── compact.py             # thin wrapper over the cheap model
│   │   ├── redaction.py           # strip account numbers / PANs before send
│   │   └── prompts/
│   │       ├── label.py
│   │       ├── parse_unknown.py
│   │       ├── confirm_intent.py
│   │       ├── narrative.py
│   │       └── ask_system.py
│   ├── agents/
│   │   ├── base.py                # Agent protocol, Tool, AgentResult
│   │   ├── registry.py            # name → agent factory
│   │   ├── context.py             # IngestRunCtx / AskCtx
│   │   ├── pipeline.py            # ingest DAG runner
│   │   ├── orchestrator.py        # conversational router for `ask`
│   │   └── subagents/
│   │       ├── ingest_pdf.py
│   │       ├── ingest_email.py
│   │       ├── ingest_sms.py
│   │       ├── normalize.py
│   │       ├── labeler.py
│   │       ├── confirm.py
│   │       ├── ledger.py
│   │       ├── cashflow.py
│   │       ├── loans.py
│   │       ├── health.py
│   │       ├── archive.py
│   │       └── report.py
│   ├── ingest/
│   │   ├── detect.py              # file type + bank fingerprint
│   │   ├── pdf/
│   │   │   ├── base.py            # StatementParser protocol
│   │   │   ├── text_extract.py    # pdfplumber
│   │   │   ├── hdfc.py
│   │   │   ├── icici.py
│   │   │   ├── sbi.py
│   │   │   ├── axis.py
│   │   │   └── generic_llm.py     # last-resort table extract
│   │   ├── email/
│   │   │   ├── mailbox.py         # eml/mbox/takeout
│   │   │   ├── gmail_api.py       # stubbed, unused until v1.1
│   │   │   └── parsers.py         # bank alert / invoice / salary mail
│   │   └── sms/
│   │       ├── loaders.py         # xml / csv / json
│   │       ├── templates.py       # Indian bank SMS regexes
│   │       └── fallback.py        # compact-model parse
│   ├── finance/                   # PURE — unit-tested hard
│   │   ├── normalize.py
│   │   ├── dedupe.py
│   │   ├── self_transfer.py
│   │   ├── cashflow.py
│   │   ├── habits.py
│   │   ├── emi.py
│   │   ├── channels.py            # DC/CC/UPI ratios
│   │   ├── salary.py
│   │   ├── gst.py
│   │   └── health.py
│   ├── reports/
│   │   ├── monthly.py             # assemble report DTO
│   │   ├── graphs.py              # plotext CLI + optional plotly HTML
│   │   └── export.py              # markdown / html / json
│   └── archive/
│       └── mover.py               # checksum + move inbox → archive
└── tests/
    ├── conftest.py
    ├── fixtures/                  # anonymized PDF snippets, SMS xml, mbox
    ├── unit/finance/
    ├── unit/ingest/
    ├── unit/agents/
    └── integration/test_ingest_pipeline.py
```

**Hard rule:** no file over ~300–400 lines without a split. Parsers, agents, and finance math never share a module.

---

## 5. Domain model

### 5.1 Core entities

**Account**
- `id`, `display_name`, `institution`, `type` (`savings|current|credit_card|wallet|upi|loan`)
- `last4`, `upi_vpas[]`, `holder_aliases[]` (used for self-transfer)
- `currency` default `INR`, `is_own=true`
- optional `credit_limit` (for CC utilization)

**AccountMonth**
- `(account_id, year, month)` unique
- `opening_balance`, `closing_balance`
- `source`: `statement` (trusted) or `computed` (from txs + prior close)
- `statement_id` if a PDF supplied the official pair

A statement is the source of truth for that month’s open/close. Computed months fill gaps and must be flagged when they disagree with a later statement.

**Transaction**
- identity: `id`, `account_id`, `posted_at`, `value_date`
- money: `amount` signed (`+` credit, `-` debit), `currency`
- raw: `description_raw`, `description_norm`, `counterparty`, `merchant`
- rails: `channel` (`upi|neft|imps|rtgs|debit_card|credit_card|atm|cash|cheque|nach|other`)
- meaning: `category`, `subcategory`, `intent`
  - `intent`: `income | expense | transfer | self_transfer | emi | loan_disbursal | refund | investment | unknown`
- GST: `gst_rate`, `gst_amount`, `gst_source` (`invoice|inferred|none`)
- provenance: `source_kind` (`pdf|email|sms`), `source_ref`, `content_hash`, `ingest_run_id`
- pairing: `duplicate_of_id`, `self_transfer_group_id`, `exclude_from_cashflow` bool
- labeling: `label_source` (`rule|model|manual`), `label_confidence`
- confirmation: `income_review` = `pending | income | transfer | skipped`

**Loan / EMI**
- Loan: principal, rate, start, tenure_months, emi_amount, lender, status, linked account
- EmiOccurrence: due date, expected amount, matched `transaction_id`, status (`paid|due|missed|partial`)

**Rule**
- Learned or hand-written: match on counterparty / UPI VPA / description regex / amount band → category + intent
- Manual labels write a Rule so the next ingest does not ask again

**IngestRun**
- timestamps, file inventory, counts (parsed / dupes / self-transfers / pending review), `archive_path`, status

### 5.2 Identity and dedupe

A transaction’s natural key is:

```
sha256(account_last4 | posted_at.date | signed_amount | normalized_desc_prefix | source_hint)
```

Same economic event arriving from PDF **and** SMS **and** email becomes **one** row plus extra `source_ref`s. SMS/email enrich the PDF row (UPI VPA, merchant, ref no) rather than inserting a second spend.

---

## 6. Feature design

### 6.1 Ingest — PDF, Gmail, SMS

**Inbox contract**

```
data/inbox/pdf/*.pdf
data/inbox/email/*.{eml,mbox,zip}     # zip = Google Takeout mail
data/inbox/sms/*.{xml,csv,json}
```

`finsca ingest` creates an `IngestRun`, then:

1. **Detect** — MIME + bank fingerprint (IFSC, “HDFC Bank”, statement period regex).
2. **Parse** — bank-specific PDF parser; else `generic_llm` on redacted text/tables.
3. **Parse email** — bank alerts, e-invoices, salary credits, CC statements.
4. **Parse SMS** — template regex first (HDFC/ICICI/SBI/Axis/PhonePe/GPay/Paytm); compact model only on misses.
5. Each parser returns `ParsedBatch` (accounts hinted, opening/closing if present, txs, warnings). Never writes the DB itself.

PDF parsers must extract **statement period + opening + closing** when the bank prints them. That is how `AccountMonth` stays honest.

Gmail v1 is **offline files**. `ingest/email/gmail_api.py` exists as a sealed module (OAuth readonly) and is not wired until v1.1 so the first report does not depend on Google Cloud setup.

### 6.2 Accounts + monthly open/close

- Accounts are upserted from statement headers and from SMS (“a/c XX1234”).
- User can `finsca accounts add` / `rename` / `alias` (aliases drive self-transfer).
- For each account-month:
  - If a statement exists → store official open/close (`source=statement`).
  - Else `closing = opening + sum(signed txs)`; next month’s opening = this close (`source=computed`).
- `finsca accounts --month 2026-08` prints a ledger table. Drift between computed and statement is a warning, not a silent overwrite.

### 6.3 Auto-label + manual label

Priority order (first hit wins, later stages can only fill blanks unless user overrides):

1. User **Rule** (including rules created by past manual labels)
2. Deterministic merchant/UPI map in `labels.yaml`
3. Compact model (`LabelerSubagent`) — batch of 25 unknown txs, structured JSON
4. Leave `unknown` rather than guess below confidence threshold (default 0.7)

`finsca label <txn_id> dining --remember` writes a Rule.

Categories (v1 taxonomy, India-shaped, kept in YAML so you can edit without code):

`salary, freelance, business_income, interest, refund, grocery, dining, transport, fuel, rent, utilities, mobile_internet, shopping, health, education, entertainment, travel, insurance, investment, tax_gst, emi, transfer, self_transfer, cash, other`

### 6.4 Cash-flow intent, habits, graphs

`finance/cashflow.py` (pure):

- **Inflow** = intents `income` + `loan_disbursal` + `refund` (refunds shown separately)
- **Outflow** = `expense` + `emi` + `investment` + `tax_gst`
- **Transfers** and **self_transfers** are **excluded** from inflow/outflow
- Net = inflow − outflow
- Savings rate = net / inflow (undefined if no confirmed income)

Habits:

- Top merchants, top categories, weekday vs weekend, ticket-size bands
- Recurring detections (same merchant ±3 days, ±5% amount, ≥3 months)
- “Intent” narrative is LLM (Grok) **over the computed numbers**, never the other way around

Graphs:

- CLI: `plotext` bars (cash flow, category, channel mix)
- File: `data/reports/<month>/report.html` via Plotly (optional extra, same DTO)

### 6.5 EMIs / active loans

Two ways a loan enters the book:

1. User: `finsca loans add --lender HDFC --emi 18420 --day 5 --principal …`
2. Detector: recurring NACH/EMI description or “EMI” SMS, same amount monthly

Each month the loan agent tries to match a debit. Unmatched → `due`/`missed`. Disbursal credits can be tagged `loan_disbursal` so they do not look like salary.

Active loan report: remaining tenure estimate, EMI/income ratio, next due, missed count.

### 6.6 DC / CC / UPI ratios, salary cycle, GST%, health

**Channel mix** — count and value share of `debit_card` / `credit_card` / `upi` among *expenses only* (self-transfers out). CC bill payments are self-transfers, not a second spend.

**Salary cycle**

- Recurring credits labeled `salary` (or pending review that looks like salary)
- Modal day-of-month, variance, last expected vs actual
- Health flag if the cycle breaks

**GST**

- From e-invoice emails (GSTIN, tax break-up) when present
- Else infer 0/5/12/18/28 from merchant category **only** when `gst_source=inferred` and shown as estimate
- Report: GST paid this month, % of taxable spend, not a CA-grade return

**Financial health score (0–100, transparent weights)**

| Signal | Weight | Healthy direction |
|---|---|---|
| Savings rate | 25 | ≥ 20% |
| EMI / confirmed income | 20 | ≤ 40% |
| CC utilization (if limit known) | 15 | ≤ 30% |
| Emergency fund months (liquid / avg expense) | 15 | ≥ 6 |
| Salary regularity | 10 | on-cycle |
| Unknown/unlabeled % | 10 | low |
| Missed EMIs | 5 | zero |

The report prints the **subscores**, not a mysterious single number. Grok writes a 1-paragraph briefing from those subscores.

### 6.7 Archive after each run

`ArchiveSubagent` runs only if the run is `success` or `partial` (some files failed, rest committed):

- `data/archive/2026-09-13_run_<ulid>/`
  - original files (same relative names)
  - `manifest.json` (sha256, parser used, tx counts, warnings)
- Inbox files are **moved**, not copied, so the inbox is empty for the next drop
- Failed files stay in inbox with a `.error.json` sidecar
- `finsca ingest --replay <run-id>` can re-read archive without user re-dropping

### 6.8 Self-transfer (no double counting)

`finance/self_transfer.py` is the most important money function. Pairing rules, in order:

1. Both legs already marked `self_transfer` by rule
2. Counterparty last4 / UPI VPA / alias ∈ user’s own accounts
3. Same absolute amount, opposite signs, ≤ 72 hours apart, two different own accounts
4. Bank → own CC (bill pay), bank → own wallet, own wallet → own bank
5. UPI to own VPA

Effect of a pair:

- `self_transfer_group_id` shared
- `intent = self_transfer`
- `exclude_from_cashflow = true`
- Still visible on each account’s statement (balances stay correct)
- Never in income, spend, GST, or habits

Ambiguous pairs (same amount, unknown counterparty) go to `finsca review` as “self-transfer?” not as income.

### 6.9 Confirm: Income source vs money transfer

Any **credit** that is not already `self_transfer` / `refund` / `loan_disbursal` and fails a high-confidence salary/interest rule is queued.

`finsca review` (interactive Rich):

```
+12,500  2026-08-04  NEFT-FOO BAR PVT  HDFC ..4521
  [I]ncome source   [T]ransfer (exclude from income)   [S]kip   [A]lways for this counterparty
```

- `I` → `intent=income`, optional category `salary|freelance|business_income|interest|other`
- `T` → `intent=transfer`, `exclude_from_cashflow=true` unless it is an expense reimbursement you choose to keep
- `A` writes a Rule on counterparty / UPI / NEFT name

`finsca ingest --yes` will **not** auto-decide these. It only auto-applies existing Rules. Unreviewed credits stay out of “confirmed income” so salary cycle and health do not lie.

---

## 7. Agent orchestration

### 7.1 Agent protocol

Every subagent is a class implementing:

```
name: str
description: str
input_model: type[BaseModel]
output_model: type[BaseModel]
tools: tuple[Tool, ...]
llm_tier: Literal["none", "compact", "openai", "grok"]

def run(self, ctx: RunContext, payload: Input) -> AgentResult[Output]
```

- `llm_tier="none"` for archive, ledger math, dedupe
- Compact for labeling / SMS leftovers / unknown merchants
- Grok for orchestrator + monthly narrative + `ask`
- OpenAI as configured peer (same interface); user can set `FINSCA_REASONING_PROVIDER=openai|grok`

No agent imports another agent’s internals. They communicate only via Pydantic payloads and the shared `RunContext` (run id, repos, settings, llm router).

### 7.2 Ingest pipeline (deterministic DAG)

```
Detect → [PdfAgent ∥ EmailAgent ∥ SmsAgent]
      → NormalizeAgent          # hash, merge sources, merchant cleanup
      → SelfTransferAgent       # pure finance + persist pairs
      → LabelerAgent            # rules then compact
      → ConfirmQueueAgent       # enqueue income-vs-transfer
      → LedgerAgent             # accounts + AccountMonth
      → LoanMatchAgent          # attach EMI hits
      → ArchiveAgent
```

Parallel only at the three parsers. Everything after is serial so hashes and pairs are stable.

Pipeline runner (`agents/pipeline.py`) logs each stage’s `AgentResult` onto `IngestRun`. A stage failure marks the run `partial` and still archives the files that parsed.

### 7.3 Conversational orchestrator (`finsca ask`)

Small supervisor (Grok by default) with **few** tools:

- `search_transactions`
- `get_month_report`
- `get_account_months`
- `get_loans`
- `get_pending_review`
- `run_subagent(name, payload)` — only for `cashflow`, `habits`, `health`, `loans`, `labeler`

It cannot write the ledger except through `labeler` / `confirm` tools that already have validation. System prompt: “Numbers come from tools. If a tool was not called, say you do not know.”

### 7.4 Why this is not one file

| File | Sole job |
|---|---|
| `agents/pipeline.py` | Order + error policy |
| `agents/orchestrator.py` | Tool-calling loop for ask |
| `agents/base.py` | Protocol |
| `agents/subagents/*.py` | One capability each |
| `finance/*.py` | Math with no I/O |
| `ingest/**` | Bytes → ParsedBatch |
| `llm/router.py` | Which model |

---

## 8. LLM support: OpenAI + compact + Grok

### 8.1 Router

`llm/router.py` maps **task → tier → provider/model**:

| Tier | Default model (config-overridable) | Used for |
|---|---|---|
| `grok` | `grok-4-5` via `https://api.x.ai/v1` (`XAI_API_KEY`) | ask, monthly narrative, health briefing |
| `openai` | `gpt-4.1` via official OpenAI (`OPENAI_API_KEY`) | optional reasoning swap; unknown-PDF fallback if set |
| `compact` | `gpt-4.1-mini` **or** `grok-4-fast` (`FINSCA_COMPACT_PROVIDER`) | labels, SMS fallback, merchant normalize |

Both Grok and OpenAI are accessed through the same `openai` Python SDK (Grok is OpenAI-compatible). Providers are two thin classes; the rest of the app only sees `LLMRouter.complete(tier, messages, schema)`.

Structured output: JSON schema / pydantic parse. Labeling never accepts free prose.

### 8.2 Cost and privacy controls

- `llm/redaction.py` masks account numbers, PANs, full VPA local-parts, phone numbers before any outbound call
- Compact batches (25 txs) with caching keyed on `description_norm`
- `FINSCA_LLM_OFF=1` runs rules-only (labels stay `unknown` rather than calling out)
- Token usage stored on `IngestRun`

### 8.3 Provider default

Reasoning defaults to xAI/Grok. OpenAI is a first-class peer. Compact is a cheap tier for high-volume classification.

---

## 9. CLI surface

```
finsca                      # status: last run, pending reviews, inbox counts
finsca ingest [--replay ID]
finsca review               # income vs transfer (+ optional self-transfer)
finsca label ID CATEGORY [--remember]
finsca accounts [list|add|alias|months]
finsca loans [list|add|close]
finsca report [--month YYYY-MM] [--html]
finsca ask "…"
finsca config               # show provider, paths, taxonomy
```

Interactive prompts use Rich `Confirm` / `Prompt`. No curses TUI in v1.

---

## 10. Config and secrets

`~/.finsca.toml` + `.env` via pydantic-settings:

```
data_dir
inbox_dir / archive_dir
reasoning_provider = grok | openai
compact_provider = openai | grok
models.grok / models.openai / models.compact
label_min_confidence = 0.7
self_transfer_window_hours = 72
llm_off = false
```

`.env.example`: `XAI_API_KEY`, `OPENAI_API_KEY`. Never commit `.env` or `data/` contents.

---

## 11. Testing strategy

- **Pure finance** (`self_transfer`, `dedupe`, `cashflow`, `health`, `gst`, `salary`): table-driven unit tests. These are the regression wall.
- **Parsers:** fixtures cut from anonymized real statements. Golden JSON per bank.
- **Agents:** fake LLM + in-memory sqlite. Assert pipeline order and that archive moves files.
- **No live API tests** in CI.

Definition of done for a stage: tests exist and pass; no “we’ll add tests later”.

---

## 12. Security / data handling

- Local SQLite only in v1
- Redact before LLM
- Archive is local; no cloud sync
- Gmail API (later) is readonly + least-privilege scope
- This is a personal bookkeeping agent, not a CA, not investment advice. GST % is indicative.

---

## 13. Out of scope for v1

- Multi-user / SaaS / hosted DB
- Live SMS reading from the phone
- Automatic tax filing, ITR, or GSTR
- Investments (MF/stocks) beyond “investment” as a category
- Receipt OCR photos
- Always-on daemon / launchd watcher (can add `finsca watch` later)
- Mobile app or web dashboard

---

## 14. Implementation phases (PR-sized)

Each phase is independently reviewable and leaves the CLI runnable.

### Phase 0 — Skeleton ✅
`pyproject.toml`, package layout, settings, sqlite schema, empty Typer app, `.env.example`, `data/**/.gitkeep`.
**Exit:** `finsca` prints “no runs yet”. **Done** — see [PROGRESS.md](PROGRESS.md).

### Phase 1 — Ledger core ✅
Domain models, repositories, `Account` / `AccountMonth` / `Transaction` CRUD, money helpers.
**Exit:** `finsca accounts add` works. **Done** — see [PROGRESS.md](PROGRESS.md).

### Phase 2 — PDF ingest + archive ✅
Detect + 1–2 bank parsers + generic fallback stub, ingest pipeline up to persist, archive mover.
**Exit:** drop a statement PDF → txs + official open/close → inbox empty. **Done** — see [PROGRESS.md](PROGRESS.md).

### Phase 3 — SMS + email files ✅
Loaders + Indian SMS templates + eml/mbox bank-alert parser. Dedupe across sources.
**Exit:** same UPI hit in SMS + PDF is one row. **Done** — see [PROGRESS.md](PROGRESS.md).

### Phase 4 — Self-transfer + review queue ✅
Pure matcher + `finsca review` for income vs transfer + rule writer.
**Exit:** own-account hop does not inflate income; user can mark a credit. **Done** — see [PROGRESS.md](PROGRESS.md).

### Phase 5 — Labeling
YAML taxonomy, rule engine, compact-model labeler, `finsca label --remember`.

### Phase 6 — Loans / EMI
Loan entity, matcher, `finsca loans`.

### Phase 7 — Report
Cash flow, habits, DC/CC/UPI, salary cycle, GST, health score, plotext + HTML.

### Phase 8 — LLM router + ask
Grok + OpenAI + compact wired; `finsca ask`; monthly narrative.

### Phase 9 — Extra bank parsers + polish
HDFC/ICICI/SBI/Axis coverage, replay, better fingerprints.

**First vertical slice:** Phase 0 → 1 → 2. That is already a useful “PDF in, balances out” CLI. Everything else stacks on that ledger.

---

## 15. Key decisions

1. **Local SQLite CLI**, not a server — matches “my finances” and keeps statements off the network.
2. **Pipeline of small subagents**, not one mega-agent — money stays deterministic; LLM is scoped.
3. **File-first ingest**, Gmail API later — unblocks v1.
4. **Self-transfer and income-confirm are first-class**, not afterthoughts — they are the difference between a real report and double-counted junk.
5. **Statement open/close beat computed balances** when both exist.
6. **Three LLM tiers** (Grok / OpenAI / compact) behind one router.
7. **Rules remember human decisions** so the CLI gets quieter over time.
8. **Modular Python package** with hard layering — no single file owns the product.

---

## 16. Progress

Live status, checklists, and the changelog are in **[PROGRESS.md](PROGRESS.md)**. This section only names the next planned slice so the design doc stays stable.

**Next implementation slice:** Phase 5 — labeling.
