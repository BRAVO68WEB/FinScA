# FinScA

Personal **Financial Services Agent** — an India-first, local, agentic CLI that turns bank-statement PDFs, Gmail exports, and SMS dumps into a monthly financial report.

Phases 0–3 are in: ledger CLI, PDF ingest, and SMS/email alerts that dedupe against the statement. Later phases are stubbed.

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
finsca accounts set-month 4521 --month 2026-08 --opening 10000 --closing 12500.50
# drop a statement into data/inbox/pdf/ then:
finsca ingest
finsca review link
finsca review list
finsca review apply <id> income --category salary --always --match "V2V CYBERSECURITY"
finsca label auto
finsca label set <id> dining --remember --match SWIGGY
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
