"""Claude-backed task priority judgement.

The trust story lives here, not in the route:

  1. tool_choice forces Claude to answer via a fixed JSON schema.
  2. The tool's input is re-validated against a Pydantic model -- schema-on-paper
     isn't trusted, it's re-checked in code.
  3. A real timeout (10s) on the client.
  4. Transport retries (timeout/connection error/retryable 5xx/429) with backoff
     and jitter -- never on 400/401/403, since those won't fix themselves.
  5. Exactly one repair retry if the *shape* is wrong: the model's own broken
     output plus the validation error is handed back, once. If that still
     fails, the input is quarantined to logs/quarantine.jsonl and a 422 is
     raised.
  6. A structured cost-log line (prompt version, model, token counts, duration,
     whether a repair was needed) is emitted per call.
  7. LLM_ENABLED=false is a kill switch; LLM_STUB=1 skips the model entirely
     for local dev / tests, at zero cost.
"""

import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal, Optional

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_TRANSPORT_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

PROMPT_VERSION = "priority-v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

QUARANTINE_PATH = Path(__file__).parent / "logs" / "quarantine.jsonl"

client = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY,
    timeout=REQUEST_TIMEOUT_SECONDS,
    max_retries=0,  # the transport-retry loop below is the only retry logic -- the
                    # SDK's own default (2) would otherwise silently stack with it
)

cost_logger = logging.getLogger("ai.cost")
if not cost_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    cost_logger.addHandler(_handler)
    cost_logger.setLevel(logging.INFO)
    cost_logger.propagate = False

_CLASSIFY_TOOL = {
    "name": "classify_priority",
    "description": "Record the urgency judgement for a task.",
    "input_schema": {
        "type": "object",
        "properties": {
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How urgent the task is.",
            },
            "reasoning": {
                "type": "string",
                "description": "One sentence explaining the judgement.",
            },
        },
        "required": ["priority", "reasoning"],
    },
}


class PriorityJudgement(BaseModel):
    priority: Literal["low", "medium", "high"]
    reasoning: str


class AIJudgementError(Exception):
    """Base class for classify_priority failures."""


class AITimeoutError(AIJudgementError):
    """The model didn't respond in time, even after retries."""


class AITransportError(AIJudgementError):
    """The model API call failed (connection error or a non-timeout status), even after retries."""


class AIValidationError(AIJudgementError):
    """The model's output failed schema validation even after one repair attempt."""


class AIDisabledError(Exception):
    """Raised when LLM_ENABLED=false -- the caller should serve a fallback/503."""


class _ShapeError(Exception):
    """Internal: the response had no usable tool_use block."""


_STUB_JUDGEMENT = PriorityJudgement(priority="medium", reasoning="Stub mode -- no model call was made.")


def _is_enabled() -> bool:
    return os.environ.get("LLM_ENABLED", "true").strip().lower() != "false"


def _is_stub() -> bool:
    return os.environ.get("LLM_STUB", "").strip() == "1"


def _retry_after_seconds(error: Exception) -> Optional[float]:
    """Retry-After can be a plain integer of seconds, or an HTTP date -- handling
    only the integer form is the exact bug the assignment warns about."""
    response = getattr(error, "response", None)
    header = response.headers.get("retry-after") if response is not None else None
    if not header:
        return None

    try:
        return max(0.0, float(header))
    except ValueError:
        pass

    try:
        return max(0.0, (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


def _sleep_with_backoff_and_jitter(attempt: int, retry_after: Optional[float] = None) -> None:
    if retry_after is not None:
        time.sleep(retry_after)
        return
    base = min(2 ** (attempt - 1), 4)
    time.sleep(base + random.uniform(0, base * 0.5))


def _call_with_transport_retries(messages):
    last_error: Optional[Exception] = None
    saw_timeout = False

    for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        try:
            return client.messages.create(
                model=MODEL,
                max_tokens=200,
                system=SYSTEM_PROMPT,
                tools=[_CLASSIFY_TOOL],
                tool_choice={"type": "tool", "name": "classify_priority"},
                messages=messages,
            )
        except anthropic.APITimeoutError as e:
            last_error = e
            saw_timeout = True
        except anthropic.APIConnectionError as e:
            last_error = e
        except anthropic.APIStatusError as e:
            last_error = e
            if e.status_code not in RETRYABLE_STATUS_CODES:
                raise AITransportError(f"Non-retryable API error ({e.status_code}): {e}") from e

        if attempt < MAX_TRANSPORT_ATTEMPTS:
            _sleep_with_backoff_and_jitter(attempt, retry_after=_retry_after_seconds(last_error))

    if saw_timeout:
        raise AITimeoutError(f"Request timed out after {MAX_TRANSPORT_ATTEMPTS} attempts: {last_error}") from last_error
    raise AITransportError(f"Request failed after {MAX_TRANSPORT_ATTEMPTS} attempts: {last_error}") from last_error


def _extract_judgement(response) -> PriorityJudgement:
    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise _ShapeError("Model reply did not include the expected tool call")
    return PriorityJudgement.model_validate(tool_use.input)


def _log_cost(response, duration_ms: float, repaired: bool) -> None:
    usage = getattr(response, "usage", None)
    cost_logger.info(json.dumps({
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "duration_ms": round(duration_ms),
        "repaired": repaired,
    }))


def _quarantine(title: str, error: Exception) -> None:
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUARANTINE_PATH.open("a") as f:
        f.write(json.dumps({
            "prompt_version": PROMPT_VERSION,
            "input": title,
            "error": str(error),
        }) + "\n")


def classify_priority(title: str) -> PriorityJudgement:
    if not _is_enabled():
        raise AIDisabledError("AI judgement is disabled (LLM_ENABLED=false)")

    if _is_stub():
        return _STUB_JUDGEMENT

    user_message = {"role": "user", "content": f"Task: {title}"}
    start = time.monotonic()

    response = _call_with_transport_retries([user_message])

    try:
        judgement = _extract_judgement(response)
    except (_ShapeError, ValidationError) as shape_error:
        repair_messages = [
            user_message,
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": (
                    f"Your previous answer was rejected for this reason: {shape_error}. "
                    "Return only corrected JSON matching the schema."
                ),
            },
        ]
        response = _call_with_transport_retries(repair_messages)

        try:
            judgement = _extract_judgement(response)
        except (_ShapeError, ValidationError) as second_error:
            _quarantine(title, second_error)
            raise AIValidationError(
                f"Model output failed validation twice; repair did not help: {second_error}"
            ) from second_error

        _log_cost(response, (time.monotonic() - start) * 1000, repaired=True)
        return judgement

    _log_cost(response, (time.monotonic() - start) * 1000, repaired=False)
    return judgement
