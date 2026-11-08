"""Tool-calling loop for `finsca ask`. Numbers come from tools."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from finsca.agents.context import (
    AskCtx,
    CashflowInput,
    HealthInput,
    IngestRunCtx,
    ReportInput,
    StageInput,
)
from finsca.agents.registry import get
from finsca.config.settings import Settings
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import loans as loan_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ledger.report import latest_month
from finsca.llm.prompts.ask_system import ASK_SYSTEM
from finsca.llm.redaction import redact
from finsca.llm.router import reasoning_complete

_MAX_TOOLS = 4
_SUBAGENTS = {"cashflow", "health", "loans", "labeler"}
_TOOLS = (
    "search_transactions",
    "get_month_report",
    "get_account_months",
    "get_loans",
    "get_pending_review",
    "run_subagent",
)
_TOOL_CONTRACT = (
    "Reply with one JSON object. "
    'Either {"tool": "<name>", "arguments": {}} or {"answer": "<text>"}. '
    f"Tools: {', '.join(_TOOLS)}. "
    "run_subagent name is cashflow, health, loans, or labeler. "
    "Habit figures are already on get_month_report."
)


def answer_question(
    session: Session,
    settings: Settings,
    question: str,
    *,
    complete: Any = None,
) -> str:
    ctx = AskCtx(settings=settings, session=session, question=question)
    fn = complete if complete is not None else reasoning_complete(settings)
    if fn is None:
        return "ask needs an API key"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": f"{ASK_SYSTEM} {_TOOL_CONTRACT}"},
        {"role": "user", "content": redact(question)},
    ]
    tool_calls = 0
    for _ in range(_MAX_TOOLS + 1):
        raw = fn(messages)
        if not isinstance(raw, dict):
            break
        tool = raw.get("tool")
        if isinstance(tool, str) and tool and tool_calls < _MAX_TOOLS:
            tool_calls += 1
            args = _arguments(raw.get("arguments"))
            result = _run_tool(ctx, tool, args)
            messages.append(
                {"role": "assistant", "content": json.dumps({"tool": tool, "arguments": args})}
            )
            messages.append(
                {
                    "role": "user",
                    "content": redact(json.dumps({"tool_result": result}, default=str)),
                }
            )
            continue
        answer = raw.get("answer")
        if isinstance(answer, str) and answer.strip():
            if tool_calls == 0:
                return "I do not know."
            return answer.strip()
        break
    return "I do not know."


def _arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if isinstance(value, dict):
        return value
    return {}


def _run_tool(ctx: AskCtx, name: str, args: dict[str, Any]) -> Any:
    try:
        if name == "search_transactions":
            return _search(ctx.session, args)
        if name == "get_month_report":
            return _month_report(ctx, args)
        if name == "get_account_months":
            return _months(ctx.session, args)
        if name == "get_loans":
            return _jsonable(loan_repo.list_all(ctx.session))
        if name == "get_pending_review":
            return _jsonable(tx_repo.list_pending_review(ctx.session))
        if name == "run_subagent":
            return _subagent(ctx, args)
        return {"error": f"unknown tool {name}"}
    except Exception as exc:
        return {"error": str(exc)}


def _search(session: Session, args: dict[str, Any]) -> Any:
    query = str(args.get("query") or args.get("text") or "").casefold()
    year, month = _year_month(args)
    rows = tx_repo.list_all(session)
    if query:
        rows = [tx for tx in rows if _matches(tx, query)]
    if year is not None and month is not None:
        rows = [tx for tx in rows if tx.posted_at.year == year and tx.posted_at.month == month]
    return _jsonable(rows[:50])


def _matches(tx: Any, query: str) -> bool:
    category = tx.category.value if tx.category else ""
    return (
        query in tx.description_raw.casefold()
        or query in (tx.merchant or "").casefold()
        or query in category.casefold()
    )


def _month_report(ctx: AskCtx, args: dict[str, Any]) -> Any:
    year, month = _year_month(args)
    if year is None or month is None:
        latest = latest_month(ctx.session)
        if latest is None:
            return {"error": "no transactions"}
        year, month = latest
    report = get("report").run(
        IngestRunCtx(settings=ctx.settings, session=ctx.session),
        ReportInput(year=year, month=month),
    ).output.report
    return _jsonable(report)


def _months(session: Session, args: dict[str, Any]) -> Any:
    year, month = _year_month(args)
    account_id = args.get("account_id")
    rows = account_repo.list_months(
        session,
        account_id=str(account_id) if account_id else None,
        year=year,
        month=month,
    )
    return _jsonable(rows)


def _subagent(ctx: AskCtx, args: dict[str, Any]) -> Any:
    name = str(args.get("name") or "")
    if name not in _SUBAGENTS:
        return {"error": f"unknown subagent {name}"}
    payload = args.get("payload") if isinstance(args.get("payload"), dict) else {}
    run_ctx = IngestRunCtx(settings=ctx.settings, session=ctx.session)
    if name == "cashflow":
        year, month = _year_month(payload)
        txs = tx_repo.list_all(ctx.session)
        if year is not None and month is not None:
            txs = [tx for tx in txs if tx.posted_at.year == year and tx.posted_at.month == month]
        result = get("cashflow").run(run_ctx, CashflowInput(transactions=txs))
    elif name == "health":
        result = get("health").run(run_ctx, _health_input(payload))
    elif name == "loans":
        result = get("loans").run(run_ctx, StageInput())
    else:
        result = get("labeler").run(run_ctx, StageInput())
    return _jsonable(result.output)


def _health_input(payload: dict[str, Any]) -> HealthInput:
    data: dict[str, Any] = {}
    for key in (
        "inflow",
        "outflow",
        "savings_rate",
        "emi_to_income",
        "cc_util",
        "emergency_months",
        "unlabeled",
    ):
        if payload.get(key) is not None:
            data[key] = Decimal(str(payload[key]))
    if payload.get("salary_regular") is not None:
        data["salary_regular"] = bool(payload["salary_regular"])
    if payload.get("missed_emis") is not None:
        data["missed_emis"] = int(payload["missed_emis"])
    return HealthInput(**data)


def _year_month(args: dict[str, Any]) -> tuple[int | None, int | None]:
    raw_month = args.get("month")
    raw_year = args.get("year")
    if isinstance(raw_month, str) and "-" in raw_month:
        year_s, month_s = raw_month.split("-", 1)
        try:
            return int(year_s), int(month_s)
        except ValueError:
            return None, None
    if raw_year is None or raw_month is None:
        return None, None
    try:
        return int(raw_year), int(raw_month)
    except (TypeError, ValueError):
        return None, None


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
