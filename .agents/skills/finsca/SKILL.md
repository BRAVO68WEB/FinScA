---
name: finsca
description: >
  Change the FinScA ledger CLI: statement parsers, ingest, review, labels,
  loans, the monthly report, or finsca ask. Use when editing this repo,
  adding a bank or SMS parser, fixing cash-flow or a card-bill pair, or
  the user runs /finsca.
---

# FinScA

Read [references/rules.md](references/rules.md) before editing.

Read [references/design.md](references/design.md) when the change adds a module, changes ingest order, or might contradict a decision already written down. Do not edit the repo `PLAN.md` so it matches a shortcut.

## Put the change in the file that already owns it

- Savings bank: `src/finsca/ingest/pdf/<bank>.py`, add it to `_PARSERS` in `ingest/pdf/base.py`, and add `tests/fixtures/statements/<bank>.txt`. Card text stays in `ingest/pdf/cards.py`.
- Alert text shared by SMS and mail: `src/finsca/ingest/sms/templates.py`. A miss may call `ingest/sms/fallback.py`. An unknown statement layout may call `ingest/pdf/generic_llm.py`, only after the bank parser and `parse_generic` return no lines.
- A figure for income, spend, savings, GST, or health: `src/finsca/finance/`. Saving it: `src/finsca/ledger/` or a repository. The matching file in `agents/subagents/` calls that function.
- Order of ingest, including replay: `src/finsca/agents/pipeline.py`.
- What `finsca ask` is allowed to call: `src/finsca/agents/orchestrator.py`.

## Prove it

```bash
.venv/bin/pytest -q
```

Run the test file you touched first if the full suite is noisy. New tests use fixtures or `tmp_path`. A model is a fake `complete` argument. Do not call the network, and do not point a test at `data/finsca.db`.

If a CLI test looks for a printed amount or a word, keep that string or change the test in the same edit.
