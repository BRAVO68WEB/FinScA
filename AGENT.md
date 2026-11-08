# FinScA

Local CLI. Python package `finsca` under `src/`. Entry point `finsca = finsca.cli.app:app`.

[PLAN.md](PLAN.md) is the design. [PROGRESS.md](PROGRESS.md) is the tracker. The phase table in PROGRESS goes stale. Do not edit PLAN so it matches a shortcut in the code.

## Leave the user's books alone

`data/finsca.db`, `data/archive/`, `data/inbox/` (apart from `.gitkeep`), `data/gmail_token.json`, `data/gmail_credentials.json`, and `data/pdf_passwords.yaml` are real. Do not open them for tests, do not ingest them, do not commit them, and do not print passwords or tokens.

Tests use `tests/fixtures/` and the `data_dir` / `db_session` fixtures. From the repo root: `.venv/bin/pytest -q`. Pytest's pythonpath is `src` and `.`.

## Where code goes

- Amounts are `Decimal`. No floats.
- Math with no I/O lives in `src/finsca/finance/`.
- Review, labels, loans, CC bill pays, and report assembly write through `src/finsca/ledger/`.
- Subagents in `src/finsca/agents/subagents/` call those modules. They do not reimplement them.
- Ingest order and parse-error policy live in `src/finsca/agents/pipeline.py`.
- Savings parsers are one bank per file, registered in `ingest/pdf/base.py`. Card statements go through `ingest/pdf/cards.py` first. "SBI CARD" is a card.
- SMS and email share `ingest/sms/templates.py`. The compact model runs only after a template or a bank parser misses, and only when a provider is configured.
- `finsca ask` is `agents/orchestrator.py`. Tools are read-only except `labeler`. There is no habits subagent. Those figures are already on the month report.
- Model calls go through `llm/router.py`, redacted first. Tests pass a fake `complete`. Missing keys and `FINSCA_LLM_OFF` must keep working.

## Git

Do not commit or push unless asked. Commits on this repo are signed. Do not pass `--no-gpg-sign`, and do not leave a changed `~/.gnupg` config behind.

Match the surrounding code. A comment only if the next reader would otherwise get the constraint wrong.
