"""
Stage 5: Positioning & Competitive Edge (Problem-Driven Only).
Input: Full artifact (problem brief, segments, competition, pain points).
Output: GTM Strategy + Positioning (competitive edge, pricing, funding, break-even).
"""
from __future__ import annotations

from typing import Any

from src.config import get_model
from src.gemini_client import generate_json
from src.models import SegmentPositioningBrief, Stage5Output, _ensure_str_list


SYSTEM = (
    "You are a strategy expert focused on positioning and GTM. You produce a clear unique competitive "
    "advantage, explicit positioning statement, perceptual map, pricing hypothesis, and one-page problem & "
    "positioning briefs per recommended segment. Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Produce a Positioning & GTM document for this opportunity (Problem-Driven mode).

ARTIFACT (summary of research so far):
{artifact_json}

Required outputs:

1. unique_competitive_advantage, positioning_summary, pricing_strategy, funding_required, break_even_summary, gtm_strategy, recommended_investors (as before).

2. positioning_statement: One explicit one-liner (e.g. "For youth with social anxiety, we offer the first deeply condition-specific digital therapeutic integrated with specialized therapists, at $X/month D2C.").

3. perceptual_map_2x2_note: Axes (e.g. "Level of clinical specialization low→high" vs "Digital tooling depth") and where we sit vs incumbents; where a hypothetical wedge sits.

4. price_anchor_per_segment: Rough price anchor for recommended segments (e.g. "$X/month D2C or $Y PMPM employer contracts").

5. segment_briefs: For each recommended segment (e.g. 1–2), a one-page brief:
   - segment_name, problem_statement (crystallized from landscape, e.g. "For youth with social anxiety, current self-help apps are generic and poorly personalized, leading to X% churn"),
   - target_user, current_alternatives, why_now,
   - proposed_offering, unique_edge, price_anchor (e.g. "$X/month D2C or $Y PMPM").

Output format (strict JSON, no markdown):
{{
  "unique_competitive_advantage": "<paragraph>",
  "positioning_summary": "<where we sit vs. competitors>",
  "positioning_statement": "<one-liner>",
  "perceptual_map_2x2_note": "<axes + where we and incumbents sit>",
  "pricing_strategy": "<paragraph>",
  "price_anchor_per_segment": "<rough anchor for recommended segments>",
  "funding_required": "<amount and use of funds>",
  "break_even_summary": "<volume and timeline>",
  "gtm_strategy": "<go-to-market summary>",
  "recommended_investors": ["<investor1>", "<investor2>"],
  "segment_briefs": [
    {{"segment_name": "<>", "problem_statement": "<>", "target_user": "<>", "current_alternatives": "<>", "why_now": "<>", "proposed_offering": "<>", "unique_edge": "<>", "price_anchor": "<>"}}
  ]
}}
"""


def _artifact_summary(artifact: dict[str, Any]) -> str:
    """Build a concise summary of artifact for the prompt (avoid huge JSON)."""
    parts = []
    parts.append(f"Industry: {artifact.get('industry') or 'N/A'}")
    stage0p = artifact.get("stage0p") or {}
    if stage0p:
        parts.append(f"Problem: {stage0p.get('problem_statement') or stage0p.get('summary') or 'N/A'}")
        parts.append(f"Target user: {stage0p.get('target_user') or 'N/A'}")
        parts.append(f"Target segment: {stage0p.get('target_segment') or 'N/A'}")
    stage1 = artifact.get("stage1") or {}
    if stage1 and stage1.get("tam_sam_som"):
        tss = stage1["tam_sam_som"]
        parts.append(f"TAM/SAM/SOM: {tss.get('tam')} / {tss.get('sam')} / {tss.get('som')}")
    s1 = artifact.get("section1") or {}
    parts.append(f"Categories: {', '.join(c.get('name') or '' for c in (s1.get('categories') or []))}")
    section2 = artifact.get("section2") or []
    for cs in section2:
        parts.append(f"Segments in {cs.get('category_name')}: {', '.join(s.get('name') or '' for s in (cs.get('segments') or []))}")
    section4 = artifact.get("section4") or []
    for cg in section4[:5]:
        moat = cg.get("moat_assessment")
        parts.append(f"Competition {cg.get('category_name')}/{cg.get('segment_name')}: moat={str(moat or '')[:200]}")
    return "\n".join(parts)


def run(artifact: dict[str, Any], model_name: str | None = None) -> Stage5Output:
    """
    Run Positioning agent (Stage 5) on the full artifact.
    Returns Stage5Output (GTM + positioning).
    """
    model = model_name or get_model("positioning")
    summary = _artifact_summary(artifact)
    prompt = PROMPT_TEMPLATE.format(artifact_json=summary)
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    investors = _ensure_str_list(data.get("recommended_investors"))

    briefs = []
    for b in data.get("segment_briefs") or []:
        if isinstance(b, dict):
            briefs.append(
                SegmentPositioningBrief(
                    segment_name=b.get("segment_name") or "",
                    problem_statement=b.get("problem_statement") or "",
                    target_user=b.get("target_user") or "",
                    current_alternatives=b.get("current_alternatives") or "",
                    why_now=b.get("why_now") or "",
                    proposed_offering=b.get("proposed_offering") or "",
                    unique_edge=b.get("unique_edge") or "",
                    price_anchor=b.get("price_anchor") or "",
                )
            )
    return Stage5Output(
        unique_competitive_advantage=data.get("unique_competitive_advantage") or "",
        positioning_summary=data.get("positioning_summary") or "",
        positioning_statement=data.get("positioning_statement") or "",
        perceptual_map_2x2_note=data.get("perceptual_map_2x2_note") or "",
        pricing_strategy=data.get("pricing_strategy") or "",
        price_anchor_per_segment=data.get("price_anchor_per_segment") or "",
        funding_required=data.get("funding_required") or "",
        break_even_summary=data.get("break_even_summary") or "",
        gtm_strategy=data.get("gtm_strategy") or "",
        recommended_investors=investors,
        segment_briefs=briefs,
    )
