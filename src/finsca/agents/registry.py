"""Name → agent. Pipeline and ask look agents up here and nowhere else."""

from __future__ import annotations

from finsca.agents.base import Agent
from finsca.agents.subagents.archive import agent as archive_agent
from finsca.agents.subagents.cashflow import agent as cashflow_agent
from finsca.agents.subagents.confirm import agent as confirm_agent
from finsca.agents.subagents.health import agent as health_agent
from finsca.agents.subagents.ingest_email import agent as email_agent
from finsca.agents.subagents.ingest_pdf import agent as pdf_agent
from finsca.agents.subagents.ingest_sms import agent as sms_agent
from finsca.agents.subagents.labeler import agent as labeler_agent
from finsca.agents.subagents.ledger import agent as ledger_agent
from finsca.agents.subagents.loans import agent as loans_agent
from finsca.agents.subagents.normalize import agent as normalize_agent
from finsca.agents.subagents.report import agent as report_agent

_AGENTS: dict[str, Agent] = {
    item.name: item
    for item in (
        pdf_agent,
        email_agent,
        sms_agent,
        normalize_agent,
        labeler_agent,
        confirm_agent,
        ledger_agent,
        cashflow_agent,
        loans_agent,
        health_agent,
        archive_agent,
        report_agent,
    )
}


def names() -> tuple[str, ...]:
    return tuple(_AGENTS)


def get(name: str) -> Agent:
    try:
        return _AGENTS[name]
    except KeyError as exc:
        known = ", ".join(names())
        raise KeyError(f"unknown agent {name!r}; known: {known}") from exc
