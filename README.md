# FinScA

Bank statements, mail, and SMS dumps go in. A SQLite ledger on this machine comes out.

Drop files in `data/inbox/`, run `finsca ingest`, then sort the credits that might be salary and label the rest. `finsca report` is the month. `finsca ask` only works once you put a key in `.env`.

The long design is [PLAN.md](PLAN.md). What has actually landed is [PROGRESS.md](PROGRESS.md).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Blank keys are fine. Ingest, review, and the report do not need a model. Gmail needs `pip install -e '.[gmail]'`. A Plotly bar in the HTML report needs `pip install -e '.[reports]'`.

Do not commit `.env`, `data/finsca.db`, or the statement files.

## Using it

`finsca` with no arguments prints the last run, how many reviews are waiting, and what is still in the inbox.

```bash
finsca accounts add "HDFC Salary" --type savings --last4 4521
finsca ingest
finsca review list
finsca review apply <id> income --category salary --always --match SALARY
finsca label auto
finsca label set <id> dining --remember --match SWIGGY
finsca loans add --name "HDFC Home" --lender HDFC --emi 18420 --day 5 --account 4521
finsca bills inject
finsca report --month 2026-08
```

`finsca ingest --replay <run-id>` reads that archive folder again and leaves the files where they are.

Gmail: put the OAuth desktop client JSON at `data/gmail_credentials.json`, then `finsca gmail login` and `finsca gmail pull --months 6`.

Locked PDFs: `finsca passwords add 01011990 --match hdfc`.

Tests: `pytest` from the repo root.

## Folders

```
data/inbox/pdf/      statements
data/inbox/email/    .eml, .mbox, Takeout
data/inbox/sms/      xml, csv, or json dump
data/archive/        one folder per ingest run
data/reports/        html from finsca report --html
data/finsca.db       the ledger
```

## Not this

No website, no accounts for other people, no reading SMS off the phone, no filing taxes.
