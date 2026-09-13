# FinScA progress

Living tracker. The design stays in [PLAN.md](PLAN.md). Update this file when a phase starts, lands, or is blocked.

**Last updated:** 2026-09-13  
**Current phase:** 1 — Ledger core (not started)  
**Last completed:** Phase 0 — Skeleton

---

## Snapshot

| Phase | Name | Status |
|---|---|---|
| 0 | Skeleton | **done** |
| 1 | Ledger core | not started |
| 2 | PDF ingest + archive | not started |
| 3 | SMS + email files | not started |
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

## Phase 1 — Ledger core (next)

**Exit:** `finsca accounts add` works.

Still to do:

- [ ] Pydantic domain DTOs in `core/models.py`
- [ ] Account / AccountMonth / Transaction repositories
- [ ] `finsca accounts list|add|alias|months`
- [ ] Money helper tests (`core/money.py` already exists)
- [ ] In-memory or tmp SQLite tests for CRUD

---

## Later phases

Checklists stay in PLAN.md §14 until the phase is opened. Do not start Phase 2 until Phase 1’s exit command works.

---

## Changelog

### 2026-09-13

- Wrote PLAN.md and set up the workspace (inbox/archive/reports, `.gitignore`, `.env.example`).
- Implemented Phase 0. CLI runs; tests pass.
- Added this file. PLAN.md now points here for live status.
