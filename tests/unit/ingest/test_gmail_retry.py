from __future__ import annotations

from types import SimpleNamespace

from finsca.ingest.email.gmail_api import _execute, _is_rate_limit


class _FakeHttpError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.resp = SimpleNamespace(status=status)


def test_rate_limit_detection() -> None:
    err = _FakeHttpError(403, "Quota exceeded for quota metric 'Total Query Cost' rateLimitExceeded")
    assert _is_rate_limit(err)
    assert not _is_rate_limit(_FakeHttpError(403, "insufficient permissions"))


def test_execute_retries_then_succeeds(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("finsca.ingest.email.gmail_api.time.sleep", sleeps.append)
    calls = {"n": 0}

    class Req:
        def execute(self):
            calls["n"] += 1
            if calls["n"] < 3:
                raise _FakeHttpError(403, "rateLimitExceeded quota")
            return {"ok": True}

    assert _execute(Req(), attempts=5) == {"ok": True}
    assert calls["n"] == 3
    assert any(wait >= 1 for wait in sleeps)
