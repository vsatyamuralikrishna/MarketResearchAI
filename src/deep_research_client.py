"""
Gemini Deep Research Agent integration via the Interactions API.
Used only for Stage 0E (Industry Scoping) when enabled — the stage that most
benefits from web-backed taxonomy, PESTEL, and classification. Other stages
use standard Gemini models.
See: https://ai.google.dev/gemini-api/docs/deep-research
"""
from __future__ import annotations

import json
import re
import time
import warnings
from typing import Any, Callable

from src.gemini_client import _get_client, get_api_key


# Deep Research agent ID (per Google docs)
DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"

# Poll every N seconds while waiting for completion
DEFAULT_POLL_INTERVAL = 15

# Max wait (minutes) before giving up
MAX_WAIT_MINUTES = 55


def _get_text_from_outputs(interaction: object) -> str:
    """Extract final text from interaction.outputs (list of Content, e.g. TextContent)."""
    outputs = getattr(interaction, "outputs", None) or []
    if not outputs:
        return ""
    # Prefer last output (final report)
    for i in range(len(outputs) - 1, -1, -1):
        out = outputs[i]
        if getattr(out, "type", None) == "text" and getattr(out, "text", None):
            return (out.text or "").strip()
        # Some SDKs may use a different shape
        if hasattr(out, "text"):
            return (out.text or "").strip()
    return ""


def run_deep_research(
    input_text: str,
    *,
    progress_callback: Callable[[str, float], None] | None = None,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL,
    store: bool = True,
) -> str:
    """
    Run the Gemini Deep Research Agent on the given prompt (background + poll).
    Returns the final report text when status is "completed".
    Raises RuntimeError if status is "failed" or max wait is exceeded.

    Args:
        input_text: The research prompt (can include formatting instructions).
        progress_callback: Optional callback(message, progress_0_to_1) for UI updates.
        poll_interval_seconds: How often to poll for completion.
        store: Must be True when background=True (per API requirement).
    """
    if not get_api_key():
        raise ValueError("GEMINI_API_KEY not set. Required for Deep Research.")

    client = _get_client()
    # Interactions API: use agent (not model), background=True, store=True (v1beta per Google docs)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*[Ii]nteractions.*experimental.*", category=UserWarning)
        interaction = client.interactions.create(
            input=input_text,
            agent=DEEP_RESEARCH_AGENT,
            background=True,
            store=store,
            api_version="v1beta",
        )

    interaction_id = getattr(interaction, "id", None)
    if not interaction_id:
        raise RuntimeError("Deep Research returned no interaction id.")

    if progress_callback:
        progress_callback("Deep Research started; waiting for results (this may take several minutes)…", 0.0)

    deadline = time.monotonic() + MAX_WAIT_MINUTES * 60
    last_progress = 0.0

    while True:
        time.sleep(poll_interval_seconds)
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"Deep Research did not complete within {MAX_WAIT_MINUTES} minutes. "
                f"Interaction id: {interaction_id}. You may check status later with this id."
            )

        try:
            interaction = client.interactions.get(id=interaction_id, api_version="v1beta")
        except Exception as e:
            if progress_callback:
                progress_callback(f"Polling… ({e})", min(0.9, last_progress + 0.05))
            continue

        status = getattr(interaction, "status", None) or ""

        if status == "completed":
            if progress_callback:
                progress_callback("Deep Research completed.", 1.0)
            text = _get_text_from_outputs(interaction)
            if not text:
                raise RuntimeError("Deep Research completed but returned no text output.")
            return text

        if status == "failed":
            err = getattr(interaction, "error", None)
            raise RuntimeError(f"Deep Research failed: {err or status}")

        if status in ("cancelled", "incomplete"):
            raise RuntimeError(f"Deep Research ended with status: {status}")

        last_progress = min(0.85, last_progress + 0.05)
        if progress_callback:
            progress_callback(f"Deep Research in progress… (status: {status})", last_progress)


def _extract_json_from_text(text: str) -> str | None:
    """Extract a ```json ... ``` block or first {...} from text."""
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


def generate_json_via_deep_research(
    prompt: str,
    *,
    system_instruction: str | None = None,
    progress_callback: Callable[[str, float], None] | None = None,
    json_instruction: str = "Your final answer must be a single valid JSON object. Output only that JSON (no markdown code fence, no extra text).",
) -> dict[str, Any]:
    """
    Run Deep Research with the given prompt, then parse the response as JSON.
    Use for research-heavy stages (e.g. industry scoping, market sizing) when
    you want web-backed, cited insights. Takes several minutes per call.

    The prompt is augmented with instructions to output JSON at the end so we
    can parse it into our structured models.
    """
    full_prompt = prompt
    if system_instruction:
        full_prompt = f"{system_instruction}\n\n{full_prompt}"
    full_prompt += f"\n\n{json_instruction}"
    raw = run_deep_research(
        full_prompt,
        progress_callback=progress_callback,
        store=True,
    )
    blob = _extract_json_from_text(raw)
    if not blob:
        raise ValueError("Deep Research response contained no JSON. Raw tail: " + (raw[-2000:] if len(raw) > 2000 else raw))
    for candidate in [blob, _try_fix_json(blob), blob.replace("\n", " ").replace("\r", " ")]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(_try_fix_json(blob.replace("\n", " ").replace("\r", " ")))
    except json.JSONDecodeError as e:
        raise ValueError("Deep Research returned invalid JSON; could not parse.") from e
