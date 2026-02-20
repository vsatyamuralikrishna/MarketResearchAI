"""
Agent 5: Decision Jury (Final Auditor).
Input: Full consolidated Research Artifact (Sections 1–4).
Output: Conflict Check, Moat Assessment, Resource Allocation ($1M), segment verdicts.
"""
from __future__ import annotations

import json
from typing import Any

from src.config import get_model
from src.gemini_client import generate_json
from src.models import JuryOutput, SegmentVerdict


SYSTEM = (
    "You are the Decision Jury for a market research report. You stress-test the findings: "
    "check consistency between growth and friction, assess moats, and recommend where to allocate capital. "
    "Respond with valid JSON only. Use no unescaped newlines or quotes inside string values; escape quotes with backslash."
)

PROMPT_TEMPLATE = """
Review the following consolidated market research artifact and answer the Jury questions.

ARTIFACT (JSON):
{artifact_json}

Jury questions — answer each in 1–3 paragraphs and provide segment-level verdicts:

1. The Conflict Check: Does the Financial Analyst's CAGR (Section 1) match the User Ethologist's reported friction (Section 3)? If the market is growing strongly but users hate existing tools, that's a "Green Flag" for a new entrant. Point out any alignment or mismatch.

2. The Moat Assessment: Given the Competition (Section 4), can a new solution actually survive? Is the "Delivery Mechanism" too expensive to acquire users? Summarize barriers and opportunities.

3. Resource Allocation: If you had $1M to spend, which specific segment offers the shortest "Time to Revenue"? Name category and segment and justify briefly.

4. Segment Verdicts: For each segment mentioned in the artifact, assign a verdict: "green" (strong opportunity), "amber" (moderate), or "red" (avoid / saturated). Include a short rationale per segment.

Output format (strict JSON only, no markdown, no code fences):
Single JSON object with keys: conflict_check, moat_assessment, resource_allocation, executive_summary, segment_verdicts.
Use \\n for line breaks inside strings. Escape any double-quote inside a string with backslash. No trailing commas.
"""


def _artifact_to_json(artifact: dict[str, Any]) -> str:
    """Convert artifact dict to JSON string for prompt. Use model_dump for Pydantic."""
    def _serialize(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return _serialize(obj.model_dump())
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialize(x) for x in obj]
        return obj
    return json.dumps(_serialize(artifact), indent=2)


def _to_str(val: Any) -> str:
    """Coerce model output to str. Handles dict/list so Pydantic never gets wrong type."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        parts = [f"{k}: {_to_str(v)}" for k, v in val.items()]
        return " | ".join(parts)
    if isinstance(val, list):
        return "; ".join(_to_str(x) for x in val)
    return str(val)


def run(artifact: dict[str, Any], model_name: str | None = None) -> JuryOutput:
    """
    Run Decision Jury on the full consolidated artifact.
    Returns JuryOutput (conflict check, moat assessment, resource allocation, verdicts).
    """
    model = model_name or get_model("decision_jury")
    artifact_json = _artifact_to_json(artifact)
    prompt = PROMPT_TEMPLATE.format(artifact_json=artifact_json)
    try:
        data = generate_json(prompt, model, system_instruction=SYSTEM)
    except ValueError:
        return JuryOutput(
            conflict_check="(Jury analysis could not be parsed; model returned invalid JSON.)",
            moat_assessment="",
            resource_allocation="",
            segment_verdicts=[],
            executive_summary="Decision Jury output was invalid or empty. You may re-run the pipeline to retry.",
        )

    verdicts = []
    for v in data.get("segment_verdicts") or []:
        if isinstance(v, dict):
            verdicts.append(
                SegmentVerdict(
                    category_name=_to_str(v.get("category_name")),
                    segment_name=_to_str(v.get("segment_name")),
                    verdict=_to_str(v.get("verdict")) or "amber",
                    rationale=_to_str(v.get("rationale")),
                )
            )

    return JuryOutput(
        conflict_check=_to_str(data.get("conflict_check")),
        moat_assessment=_to_str(data.get("moat_assessment")),
        resource_allocation=_to_str(data.get("resource_allocation")),
        segment_verdicts=verdicts,
        executive_summary=_to_str(data.get("executive_summary")),
    )
