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
from src.models import (
    AttractivenessRow,
    JuryOutput,
    ScenarioAnalysis,
    SegmentVerdict,
)


SYSTEM = (
    "You are the Decision Jury for a market research report. You stress-test the findings, "
    "produce segment attractiveness scores, scenario analysis, and a McKinsey-style slide outline. "
    "Respond with a single valid JSON object only: no markdown, no code fences, no text before or after. "
    "Inside string values use \\n for line breaks and \\\" for quotes. Keep each string value on one line when possible. No trailing commas."
)

PROMPT_TEMPLATE = """
Review the following consolidated market research artifact and answer the Jury questions.

ARTIFACT (JSON):
{artifact_json}

Jury questions:

1. Conflict Check, Moat Assessment, Resource Allocation, Segment Verdicts, executive_summary (as before).

2. Synthesis (Stage 6): opportunity_heat_map_summary, strategic_recommendations, next_steps; synthesis_type "landscape" or "strategy".

3. segment_attractiveness_table: Build a scoring table. Rows = key segments from the artifact. Columns: segment_name, category_name, size_score (e.g. 1-5 or Low/Med/High), growth_score, competition_intensity, accessibility, regulatory_risk, overall_score. Fill for each segment.

4. scenario_analysis: For the top recommended segment only, provide: segment_name, base_case (outcome under base assumptions), best_case, worst_case, assumptions_note (e.g. adoption, reimbursement, CAC).

5. slide_outline: McKinsey-style 10-12 slide deck outline. Array of objects: slide_number (1-12), title, bullets (array of 2-5 strings). Suggested structure: 1 Title, 2 Executive summary, 3 Industry definition & value chain, 4 Category taxonomy, 5 Market size by category/segment, 6-7 Segment deep-dives, 8 Competitive moats & gaps, 9 Opportunity heat map + attractiveness, 10 Next steps / problem-driven follow-on. Ensure all tables referenced in slides are numerically complete (no blank CAGRs/SOM where in scope).

Output: One JSON object only (no markdown, no ```). Required keys: conflict_check, moat_assessment, resource_allocation, executive_summary, segment_verdicts (array of {{category_name, segment_name, verdict, rationale}}), synthesis_type, opportunity_heat_map_summary, segment_attractiveness_table (array of {{segment_name, category_name, size_score, growth_score, competition_intensity, accessibility, regulatory_risk, overall_score}}), scenario_analysis (object: segment_name, base_case, best_case, worst_case, assumptions_note), strategic_recommendations (array of strings), next_steps (array of strings), slide_outline (array of {{slide_number, title, bullets}}). Use \\n in strings for line breaks; escape \" as \\\". No trailing commas.
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


def _ensure_str_list(x: Any) -> list[str]:
    """Coerce to list of strings; LLM sometimes returns a single string for list fields."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    if isinstance(x, str):
        return [x] if x.strip() else []
    return []


def run(artifact: dict[str, Any], model_name: str | None = None) -> JuryOutput:
    """
    Run Decision Jury on the full consolidated artifact.
    Returns JuryOutput (conflict check, moat assessment, resource allocation, verdicts).
    Uses a larger token limit and one retry on parse failure (Jury JSON is large and often truncated).
    """
    model = model_name or get_model("decision_jury")
    artifact_json = _artifact_to_json(artifact)
    prompt = PROMPT_TEMPLATE.format(artifact_json=artifact_json)
    # Allow full Jury output (verdicts, attractiveness table, scenario, slide outline). Use high ceiling;
    # the API will cap at the model's actual limit—we never want to truncate large responses.
    max_tokens = 65536
    data = None
    for attempt in range(2):  # initial + 1 retry
        try:
            data = generate_json(
                prompt,
                model,
                system_instruction=SYSTEM,
                max_output_tokens=max_tokens,
            )
            break
        except ValueError:
            if attempt == 1:
                return JuryOutput(
                    conflict_check="(Jury analysis could not be parsed; model returned invalid JSON.)",
                    moat_assessment="",
                    resource_allocation="",
                    segment_verdicts=[],
                    executive_summary="Decision Jury output was invalid or empty. You may re-run the pipeline to retry.",
                )
            # Retry once (model sometimes returns valid JSON on second try)
            continue
    if data is None:
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

    recs = data.get("strategic_recommendations")
    steps = data.get("next_steps")

    attr_table = []
    for row in data.get("segment_attractiveness_table") or []:
        if isinstance(row, dict):
            attr_table.append(
                AttractivenessRow(
                    segment_name=_to_str(row.get("segment_name")),
                    category_name=_to_str(row.get("category_name")),
                    size_score=_to_str(row.get("size_score")),
                    growth_score=_to_str(row.get("growth_score")),
                    competition_intensity=_to_str(row.get("competition_intensity")),
                    accessibility=_to_str(row.get("accessibility")),
                    regulatory_risk=_to_str(row.get("regulatory_risk")),
                    overall_score=_to_str(row.get("overall_score")),
                )
            )
    scen = data.get("scenario_analysis")
    if isinstance(scen, dict):
        scenario_analysis = ScenarioAnalysis(
            segment_name=_to_str(scen.get("segment_name")),
            base_case=_to_str(scen.get("base_case")),
            best_case=_to_str(scen.get("best_case")),
            worst_case=_to_str(scen.get("worst_case")),
            assumptions_note=_to_str(scen.get("assumptions_note")),
        )
    else:
        scenario_analysis = None

    slide_outline = data.get("slide_outline")
    if isinstance(slide_outline, list):
        outline_list = []
        for s in slide_outline:
            if isinstance(s, dict):
                outline_list.append({
                    "slide_number": int(s.get("slide_number") or 0),
                    "title": _to_str(s.get("title")),
                    "bullets": _ensure_str_list(s.get("bullets")),
                })
    else:
        outline_list = []

    return JuryOutput(
        conflict_check=_to_str(data.get("conflict_check")),
        moat_assessment=_to_str(data.get("moat_assessment")),
        resource_allocation=_to_str(data.get("resource_allocation")),
        segment_verdicts=verdicts,
        executive_summary=_to_str(data.get("executive_summary")),
        synthesis_type=_to_str(data.get("synthesis_type")),
        opportunity_heat_map_summary=_to_str(data.get("opportunity_heat_map_summary")),
        segment_attractiveness_table=attr_table,
        scenario_analysis=scenario_analysis,
        strategic_recommendations=_ensure_str_list(recs),
        next_steps=_ensure_str_list(steps),
        slide_outline=outline_list,
    )
