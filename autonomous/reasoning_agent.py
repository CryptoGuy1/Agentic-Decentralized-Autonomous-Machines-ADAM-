# autonomous/reasoning_agent.py
import os
import json
import logging
from typing import Any, Dict, List

from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# initialize client (make sure OPENAI_API_KEY is in your .env)
client = OpenAI()

# Model name from .env; default to a chat-capable GPT-4-mini style model
MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "gpt-4o-mini")

DEFAULT_SYSTEM_PROMPT = (
    "You are Veri-ADAM Reasoner. Respond ONLY with JSON following this schema: "
    '{"decision":"escalate|monitor|ignore", "reason":["..."], "recommended_action":"...", "confidence":float}'
)


def _extract_text_from_chat_response(resp: Any) -> str:
    """
    Extract text from a chat completion response in a robust way across SDK shapes.
    """
    # Try the common chat shape: resp.choices[0].message.content
    try:
        choices = getattr(resp, "choices", None) or (resp.get("choices") if isinstance(resp, dict) else None)
        if choices:
            first = choices[0]
            # If first is dict-like:
            if isinstance(first, dict):
                # support both OpenAI-style {"message": {"content": "..."}}
                msg = first.get("message")
                if isinstance(msg, dict):
                    return msg.get("content", "")
                # older form: {"text": "..."}
                if "text" in first:
                    return first["text"]
            else:
                # object-like: try attributes
                msg = getattr(first, "message", None)
                if msg is not None:
                    return getattr(msg, "content", "")
                text_attr = getattr(first, "text", None)
                if text_attr:
                    return text_attr
    except Exception:
        pass

    # Some wrappers have choices -> delta streaming content, try concatenating
    try:
        if isinstance(choices, list):
            parts: List[str] = []
            for c in choices:
                if isinstance(c, dict):
                    m = c.get("message") or {}
                    if isinstance(m, dict):
                        parts.append(m.get("content", "") or "")
                    else:
                        parts.append(c.get("text", "") or "")
                else:
                    # object-like
                    m = getattr(c, "message", None)
                    if m:
                        parts.append(getattr(m, "content", "") or "")
                    else:
                        parts.append(getattr(c, "text", "") or "")
            joined = "".join(parts).strip()
            if joined:
                return joined
    except Exception:
        pass

    # fallback: try resp.get("output") or resp.output_text()
    try:
        output_text = getattr(resp, "output_text", None)
        if callable(output_text):
            t = resp.output_text()
            if t:
                return t
    except Exception:
        pass

    try:
        if isinstance(resp, dict):
            # attempt to find a textual field
            for key in ("text", "response", "result"):
                if resp.get(key):
                    return resp.get(key)
            # fallback: stringify
            return json.dumps(resp)
    except Exception:
        pass

    # final fallback
    return str(resp)


def call_chatgpt_reasoner(anomalies: List[Dict], context_readings: List[Dict] | None = None) -> Dict:
    """
    Use a chat-capable GPT model (e.g. gpt-4o-mini) to reason about anomalies.
    - anomalies: list of flagged readings (dicts)
    - context_readings: optional list of recent readings for context
    Returns a dict with at least keys: 'decision' and 'confidence'
    """
    if context_readings is None:
        context_readings = []

    # Build the user payload
    user_payload = {"anomalies": anomalies, "context_readings": context_readings}
    user_text = json.dumps(user_payload, default=str)

    logger.info("Using chat model: %s", MODEL_NAME)

    # Build messages (system + user)
    messages = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": "INPUT:\n" + user_text}
    ]

    # Call the chat completions API
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=800,
            temperature=0.0,
        )
    except Exception as e:
        logger.exception("LLM call failed")
        raise RuntimeError(f"LLM call error: {e}") from e

    # Extract raw text
    raw_text = _extract_text_from_chat_response(resp)
    logger.info("Raw LLM output (truncated): %s", raw_text[:2000])

    # Parse JSON from the returned text
    try:
        text = raw_text.strip()
        # find first JSON object inside returned text (in case assistant added commentary)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_blob = text[start:end + 1]
        else:
            json_blob = text
        result = json.loads(json_blob)
    except Exception as e:
        logger.exception("Failed to parse LLM JSON output")
        raise ValueError("Unable to parse LLM output as JSON") from e

    # Validate
    if "decision" not in result or "confidence" not in result:
        raise ValueError("LLM output missing required fields (decision/confidence)")

    return result
