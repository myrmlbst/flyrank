"""Tests for ai.classify_priority.

The Anthropic client is monkeypatched with fakes so these run without a real
API key, network access, or cost. Each test targets one piece of the trust
story: schema validation, the repair retry, transport retries, the stub
mode, and the kill switch.
"""

import json

import anthropic
import pytest

import ai


class FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, input_):
        self.input = input_


class FakeUsage:
    def __init__(self, input_tokens=100, output_tokens=20):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class FakeResponse:
    def __init__(self, content, usage=None):
        self.content = content
        self.usage = usage or FakeUsage()


def make_response(priority="high", reasoning="Sounds urgent.", **kwargs):
    return FakeResponse([FakeToolUseBlock({"priority": priority, "reasoning": reasoning})], **kwargs)


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch):
    monkeypatch.setattr(ai.time, "sleep", lambda _: None)


@pytest.fixture(autouse=True)
def _quarantine_to_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "QUARANTINE_PATH", tmp_path / "quarantine.jsonl")


def test_valid_reply_is_returned_on_first_try(monkeypatch):
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return make_response(priority="high", reasoning="Deadline is today.")

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    result = ai.classify_priority("File the tax report before 5pm today")

    assert result.priority == "high"
    assert result.reasoning == "Deadline is today."
    assert len(calls) == 1


def test_request_uses_system_prompt_file_and_forces_the_tool(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return make_response()

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    ai.classify_priority("Buy milk")

    assert captured["system"] == ai.SYSTEM_PROMPT
    assert "classify_priority" in ai.SYSTEM_PROMPT
    assert captured["tool_choice"] == {"type": "tool", "name": "classify_priority"}
    assert captured["tools"][0]["name"] == "classify_priority"


def test_stub_mode_never_calls_the_api(monkeypatch):
    monkeypatch.setenv("LLM_STUB", "1")

    def fake_create(**kwargs):
        raise AssertionError("stub mode must not call the API")

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    result = ai.classify_priority("Anything at all")

    assert result.priority in ("low", "medium", "high")


def test_kill_switch_disables_without_calling_the_api(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "false")

    def fake_create(**kwargs):
        raise AssertionError("disabled mode must not call the API")

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with pytest.raises(ai.AIDisabledError):
        ai.classify_priority("Anything at all")


def test_invalid_shape_triggers_exactly_one_repair_then_succeeds(monkeypatch):
    responses = [
        make_response(priority="urgent!!", reasoning="not a valid enum value"),
        make_response(priority="medium", reasoning="Recovered on repair."),
    ]
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    result = ai.classify_priority("Water the plants")

    assert result.priority == "medium"
    assert len(calls) == 2
    repair_prompt = calls[1]["messages"][-1]["content"]
    assert "rejected" in repair_prompt


def test_repair_failure_raises_validation_error_and_writes_quarantine(monkeypatch):
    def fake_create(**kwargs):
        return make_response(priority="not-a-real-priority", reasoning="still broken")

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with pytest.raises(ai.AIValidationError):
        ai.classify_priority("Organize desk drawer")

    lines = ai.QUARANTINE_PATH.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["input"] == "Organize desk drawer"
    assert entry["prompt_version"] == ai.PROMPT_VERSION


def test_no_tool_call_in_reply_counts_as_shape_failure(monkeypatch):
    def fake_create(**kwargs):
        return FakeResponse([])

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with pytest.raises(ai.AIValidationError):
        ai.classify_priority("Some task")


def test_timeout_exhausted_raises_ai_timeout_error(monkeypatch):
    attempts = {"count": 0}

    def fake_create(**kwargs):
        attempts["count"] += 1
        raise anthropic.APITimeoutError(request=None)

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with pytest.raises(ai.AITimeoutError):
        ai.classify_priority("Task that always times out")

    assert attempts["count"] == ai.MAX_TRANSPORT_ATTEMPTS


def test_timeout_is_retried_then_succeeds(monkeypatch):
    attempts = {"count": 0}

    def fake_create(**kwargs):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise anthropic.APITimeoutError(request=None)
        return make_response(priority="low", reasoning="No rush.")

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    result = ai.classify_priority("Someday maybe reorganize the garage")

    assert result.priority == "low"
    assert attempts["count"] == 2


def test_non_retryable_status_error_fails_immediately(monkeypatch):
    attempts = {"count": 0}

    def fake_create(**kwargs):
        attempts["count"] += 1
        raise anthropic.BadRequestError(
            message="bad request",
            response=_fake_httpx_response(400),
            body=None,
        )

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with pytest.raises(ai.AITransportError):
        ai.classify_priority("Task")

    assert attempts["count"] == 1


def test_retryable_status_error_exhausted_raises_transport_error(monkeypatch):
    attempts = {"count": 0}

    def fake_create(**kwargs):
        attempts["count"] += 1
        raise anthropic.InternalServerError(
            message="internal error",
            response=_fake_httpx_response(500),
            body=None,
        )

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with pytest.raises(ai.AITransportError):
        ai.classify_priority("Task")

    assert attempts["count"] == ai.MAX_TRANSPORT_ATTEMPTS


def test_429_with_retry_after_header_is_respected_over_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ai.time, "sleep", lambda s: sleeps.append(s))

    attempts = {"count": 0}

    def fake_create(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise anthropic.RateLimitError(
                message="rate limited",
                response=_fake_httpx_response(429, headers={"retry-after": "7"}),
                body=None,
            )
        return make_response(priority="low", reasoning="Fine.")

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    result = ai.classify_priority("Task")

    assert result.priority == "low"
    assert sleeps == [7.0]


def test_successful_call_logs_cost_with_token_counts(monkeypatch, caplog):
    def fake_create(**kwargs):
        return make_response(usage=FakeUsage(input_tokens=123, output_tokens=45))

    monkeypatch.setattr(ai.client.messages, "create", fake_create)

    with caplog.at_level("INFO", logger="ai.cost"):
        ai.classify_priority("Buy milk")

    logged = json.loads(caplog.records[-1].message)
    assert logged["input_tokens"] == 123
    assert logged["output_tokens"] == 45
    assert logged["prompt_version"] == ai.PROMPT_VERSION
    assert logged["repaired"] is False


def _fake_httpx_response(status_code, headers=None):
    import httpx

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx.Response(status_code, request=request, headers=headers)
