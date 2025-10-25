# autonomous/reasoning_agent.py
import os
import requests
import json
from typing import Dict
from openai import OpenAI

# 2. The OpenAI library automatically looks for the OPENAI_API_KEY variable
client = OpenAI() 

# 3. Get the model name from your .env file
O1_MODEL_NAME = os.getenv("O1_MODEL_NAME")

DEFAULT_SYSTEM_PROMPT = (
    "You are Veri-ADAM Reasoner. Respond ONLY with JSON following this schema: "
    '{"decision":"escalate|monitor|ignore", "reason":["..."], "recommended_action":"...", "confidence":float}'
)

def call_chatgpt_reasoner(context: Dict) -> Dict:
    """
    Sends a concise structured prompt to the ChatGPT endpoint and expects strict JSON back.
    Make sure your ChatGPT wrapper returns the raw model text in a top-level 'text' or 'response' field.
    """
    if CHATGPT_URL is None:
        raise RuntimeError("CHATGPT_URL not set")

    prompt = DEFAULT_SYSTEM_PROMPT + "\n\nINPUT:\n" + json.dumps(context, default=str)
    payload = {
        "prompt": prompt,
        "max_tokens": 300,
        "temperature": 0.0
    }
    headers = {}
    if CHATGPT_API_KEY:
        headers["Authorization"] = f"Bearer {CHATGPT_API_KEY}"
    # Many self-hosted wrappers return different shapes; adapt as needed.
    r = requests.post(CHATGPT_URL, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    resp = r.json()
    # attempt to find text
    text = resp.get("text") or resp.get("response") or resp.get("result") or resp.get("data")
    if isinstance(text, dict):
        # If wrapper already returned parsed JSON
        return text
    if isinstance(text, list):
        text = text[0]
    # else assume string
    try:
        result = json.loads(text)
    except Exception:
        # as a fallback, try if top-level choices exist (OpenAI-like)
        choices = resp.get("choices")
        if choices:
            try:
                result = json.loads(choices[0]["text"])
            except Exception as e:
                raise ValueError("Unable to parse LLM output as JSON") from e
        else:
            raise ValueError("Unable to parse LLM output as JSON")
    # Basic validation
    if "decision" not in result or "confidence" not in result:
        raise ValueError("LLM output missing required fields (decision/confidence)")
    return result
