# FinScA

Personal **Financial Services Agent** — an India-first, local, agentic CLI that turns bank-statement PDFs, Gmail exports, and SMS dumps into a monthly financial report.

Phases 0–1 are in: Typer CLI, settings, SQLite ledger, and `finsca accounts`. Later phases are stubbed.

- Design: **[PLAN.md](PLAN.md)**
- Live tracker: **[PROGRESS.md](PROGRESS.md)**

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
finsca            # prints "no runs yet"
finsca config
finsca accounts add "HDFC Salary" --type savings --last4 4521
finsca accounts list
pytest
```

## Workspace

```
data/inbox/pdf/      drop bank-statement PDFs here
data/inbox/email/    drop .eml / .mbox / Takeout here
data/inbox/sms/      drop SMS dump (xml / csv / json) here
data/archive/        ingest runs will move files here
data/reports/        generated monthly reports
```

Copy `.env.example` to `.env` when you add API keys. Never commit `.env` or statement files.

## Not in v1

No web app, no multi-user server, no live phone SMS, no tax filing.
