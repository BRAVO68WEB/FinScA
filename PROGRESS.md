# FinScA progress

Living tracker. The design stays in [PLAN.md](PLAN.md). Update this file when a phase starts, lands, or is blocked.

**Last updated:** 2026-09-13  
**Current phase:** 4 — Self-transfer + review queue (not started)  
**Last completed:** Phase 3 — SMS + email files

---

## Snapshot

| Phase | Name | Status |
|---|---|---|
| 0 | Skeleton | **done** |
| 1 | Ledger core | **done** |
| 2 | PDF ingest + archive | **done** |
| 3 | SMS + email files | **done** |
| 4 | Self-transfer + review queue | not started |
| 5 | Labeling | not started |
| 6 | Loans / EMI | not started |
| 7 | Report | not started |
| 8 | LLM router + ask | not started |
| 9 | Extra bank parsers + polish | not started |

Exit criteria for each phase are in [PLAN.md §14](PLAN.md#14-implementation-phases-pr-sized).

---

## Phase 0 — Skeleton

**Exit:** `finsca` prints “no runs yet”. **Met.**

Shipped:

- [x] `pyproject.toml` (Hatchling, `finsca` console script, pytest)
- [x] `src/finsca` package tree matching PLAN.md §4
- [x] Settings via `FINSCA_*` / `.env` (`config/settings.py`)
- [x] Default taxonomies: `config/labels.yaml`, `config/banks.yaml`
- [x] SQLite schema: accounts, account_months, transactions, loans, emi_occurrences, rules, ingest_runs, ingest_files
- [x] Engine / session helpers; `create_all` on first CLI run
- [x] Typer app: default status, `finsca config`, other commands stubbed by phase
- [x] Inbox / archive / reports dirs with `.gitkeep`
- [x] Later-phase modules as docstring stubs only (no fake logic)

Verified:

- `pytest` — 4 passed (`settings`, `schema` tables, CLI status)
- `finsca` → `no runs yet` / `inbox pdf=0 email=0 sms=0` / `pending reviews 0`
- `finsca config` prints providers and paths
- `finsca ingest` → `not implemented yet (Phase 2)`

Not in Phase 0 (intentionally):

- Account / transaction CRUD
- PDF / SMS / email parsers
- LLM calls

---

## Phase 1 — Ledger core

**Exit:** `finsca accounts add` works. **Met.**

Shipped:

- [x] Pydantic DTOs in `core/models.py` (`Account`, `AccountMonth`, `Transaction` + `New*` inputs)
- [x] Account / AccountMonth / Transaction repositories
- [x] `finsca accounts list|add|alias|rename|months|set-month`
- [x] Money helper tests
- [x] tmp SQLite CRUD + CLI tests

Verified:

- `pytest` — 16 passed
- `finsca accounts add "HDFC Salary" --type savings --last4 4521`
- `finsca accounts list` / `alias` / `set-month` / `months --account`
- id prefix resolve; computed cannot overwrite statement months

Branch: `phase-1-ledger-core`

---

## Phase 2 — PDF ingest + archive

**Exit:** drop a statement PDF → txs + official open/close → inbox empty. **Met.**

Shipped:

- [x] Inbox PDF detect + bank fingerprint (HDFC / ICICI / SBI / Axis)
- [x] Generic regex parser + HDFC withdrawal/deposit columns
- [x] Persist accounts, statement months, transactions (dupes skipped)
- [x] Archive mover: `data/archive/YYYY-MM-DD_run_<id>/` + `manifest.json`
- [x] Failed files stay in inbox with `.error.json`
- [x] `finsca ingest`

Verified:

- `pytest` — 34 passed
- Drop HDFC sample PDF → 2 txs, statement open/close, inbox `pdf=0`

Branch: `phase-2-pdf-ingest`

---

## Phase 3 — SMS + email files

**Exit:** same UPI hit in SMS + PDF is one row. **Met.**

Shipped:

- [x] SMS XML / CSV / JSON loaders
- [x] Indian bank-alert templates (amount, last4, date, debit/credit)
- [x] eml / mbox / zip email loaders, same templates
- [x] Cross-source same-event merge (account + date + amount)
- [x] Hash no longer includes source kind
- [x] Inbox ingest for pdf + email + sms; archive keeps relative paths

Verified:

- `pytest` — 43 passed
- PDF then SMS: `dupes=2`, still one UPI debit and one NEFT credit

Branch: `phase-3-sms-email`

---

## Phase 4 — Self-transfer + review queue (next)

**Exit:** own-account hop does not inflate income; user can mark a credit.

Still to do:

- [ ] `finance/self_transfer.py` matcher
- [ ] `finsca review` income vs transfer
- [ ] Rule writer from review answers

---

## Later phases

Checklists stay in PLAN.md §14 until the phase is opened. Do not start Phase 5 until Phase 4’s exit works.

---

## Changelog

### 2026-09-13

- Wrote PLAN.md and set up the workspace (inbox/archive/reports, `.gitignore`, `.env.example`).
- Implemented Phase 0. CLI runs; tests pass.
- Added this file. PLAN.md now points here for live status.
- Implemented Phase 1 on branch `phase-1-ledger-core`: accounts ledger + CLI.
- Review fixes on `phase-1-ledger-core`: one DTO per entity, JSON alias/VPA lists, id-prefix resolve, statement-wins `set_month`, flattened `accounts set-month`, unique transaction hash.
- Merged Phase 1 to main. Implemented Phase 2 on `phase-2-pdf-ingest`.
- Phase 2 review: commit then archive, savepoint per file, require last4, header vs line parse, drop unused subagent wrappers.
- Implemented Phase 3 on `phase-3-sms-email`: SMS/email ingest + cross-source dedupe.
- Phase 3 review: one event_key (account+date+paise), AlertRecord pipeline, persist months only with balances, loaders raise ParseError.
