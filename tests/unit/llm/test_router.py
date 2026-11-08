"""Router stays offline unless a key is present, and providers redact first."""

from __future__ import annotations

from types import SimpleNamespace

from finsca.config.settings import Settings
from finsca.llm.openai_provider import OpenAIProvider
from finsca.llm.redaction import redact
from finsca.llm.router import LLMRouter, compact_complete


def test_redact_masks_vpa_local_part_and_phone() -> None:
    text = redact("paid alice.j@okaxis from 9876543210 PAN ABCDE1234F")
    assert "alice.j" not in text
    assert "@okaxis" in text
    assert "9876543210" not in text
    assert "ABCDE1234F" not in text


def test_compact_complete_is_none_when_llm_is_off(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert compact_complete(Settings(llm_off=True)) is None


def test_compact_complete_is_none_without_a_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    assert compact_complete(Settings(llm_off=False, compact_provider="openai")) is None


def test_provider_redacts_message_before_the_client_sees_it() -> None:
    captured: dict[str, object] = {}

    class _Completions:
        def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            message = SimpleNamespace(content='{"labels": []}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    provider = OpenAIProvider("test-key", "gpt-4.1-mini")
    parsed = provider.complete(
        [{"role": "user", "content": "UPI alice@oksbi 9988776655"}],
        client=client,
    )
    assert parsed == {"labels": []}
    messages = captured["messages"]
    assert isinstance(messages, list)
    body = messages[0]["content"]
    assert "alice" not in body
    assert "9988776655" not in body
    assert "@oksbi" in body


def test_router_complete_returns_none_when_off(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    router = LLMRouter(Settings(llm_off=True))
    assert router.complete("grok", [{"role": "user", "content": "hi"}]) is None
