"""
Thin wrapper over Google Gemini API (google-genai SDK): model selection, retries, token limits.
Uses Gemini 2.5 models per https://ai.google.dev/gemini-api/docs/models
"""
import json
import os
import re
import time
from typing import Any

from google import genai
from google.genai import types

# Default models (Gemini 2.5 per official docs). Override via config.yaml.
# See https://ai.google.dev/gemini-api/docs/models
DEFAULT_MODELS = {
    "taxonomy": "gemini-2.5-pro",
    "segment_specialist": "gemini-2.5-flash",
    "behavioral_ethologist": "gemini-2.5-flash",
    "competitive_strategist": "gemini-2.5-pro",
    "decision_jury": "gemini-2.5-pro",
}

# Retry config
MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0

_client: genai.Client | None = None


def get_api_key() -> str:
    """Get Gemini API key from env or Streamlit secrets."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            return st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY") or ""
    except Exception:
        pass
    return ""


def _get_client() -> genai.Client:
    """Return a configured Client (uses GEMINI_API_KEY from env if set)."""
    global _client
    if _client is not None:
        return _client
    key = get_api_key()
    if key:
        _client = genai.Client(api_key=key)
    else:
        _client = genai.Client()
    return _client


def _is_retryable(e: Exception) -> bool:
    """Whether to retry (rate limit, transient). Do not retry NotFound."""
    msg = str(e).lower()
    if "not found" in msg or "404" in str(e):
        return False
    if "429" in str(e) or "resource exhausted" in msg or "rate" in msg:
        return True
    if "unavailable" in msg or "503" in str(e):
        return True
    return False


def generate(
    prompt: str,
    model_name: str,
    *,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 8192,
) -> str:
    """
    Call Gemini with the given prompt and model. Retries on rate limit/transient errors.
    Returns the raw text response.
    """
    key = get_api_key()
    if not key:
        raise ValueError("GEMINI_API_KEY not set. Add it to .env or Streamlit secrets.")

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction or None,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    last_error: Exception | None = None
    backoff = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if response and getattr(response, "text", None):
                return response.text.strip()
            return ""
        except Exception as e:
            last_error = e
            if not _is_retryable(e) or attempt == MAX_RETRIES - 1:
                raise
            time.sleep(backoff)
            backoff *= 2

    if last_error:
        raise last_error
    return ""


def extract_json_block(text: str) -> str | None:
    """Extract a ```json ... ``` block from markdown, or first {...} from text."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return None


def _try_fix_json(blob: str) -> str:
    """Fix trailing commas before } or ]."""
    blob = re.sub(r",\s*}", "}", blob)
    blob = re.sub(r",\s*]", "]", blob)
    return blob


def generate_json(
    prompt: str,
    model_name: str,
    *,
    system_instruction: str | None = None,
) -> dict[str, Any]:
    """
    Call Gemini and parse response as JSON. Extracts JSON from markdown blocks.
    On parse failure, tries fixing trailing commas; then tries replacing newlines with spaces.
    """
    raw = generate(
        prompt,
        model_name,
        system_instruction=system_instruction,
    )
    blob = extract_json_block(raw)
    if not blob:
        raise ValueError("No JSON found in model response")
    for candidate in [blob, _try_fix_json(blob), blob.replace("\n", " ").replace("\r", " ")]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(_try_fix_json(blob.replace("\n", " ").replace("\r", " ")))
    except json.JSONDecodeError:
        raise ValueError("Model returned invalid JSON; could not parse or fix.") from None
