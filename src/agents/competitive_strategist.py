"""
Agent 4: Competitive Strategist.
Input: Same segment + pain points (Section 3 slice).
Output: Section 4 slice — delivery mechanism, gaps, moat assessment.
"""
from __future__ import annotations

from typing import Any

from src.config import get_model
from src.gemini_client import generate_json
from src.models import BattleCard, CompetitionGaps, PainPoints


def _ensure_str_list(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    if isinstance(x, str):
        return [x] if x.strip() else []
    return []


def _to_str(v: Any) -> str:
    """Coerce to str; LLM sometimes returns dict/list for these fields."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return " | ".join(f"{k}: {_to_str(x)}" for k, x in v.items())
    if isinstance(v, list):
        return "; ".join(_to_str(x) for x in v)
    return str(v)


SYSTEM = (
    "You are a Competitive Strategist in market research. You map how the market "
    "responds to user pains: delivery mechanisms, product/experience gaps, and moats. "
    "Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Analyze competition and gaps for this segment, given user pain points.

Category: {category_name}
Segment: {segment_name}

User pain points (Section 3):
- Zero Moment of Truth: {zmot}
- Alternative paths: {alternative_paths}
- Retention killers: {retention_killers}

Research questions:
1. Delivery mechanisms: API, Managed Service, Mobile App, SaaS? List all that apply.
2. Product feature gaps vs. experience gaps; moat assessment.
3. Porter's Five Forces: Run explicitly for this segment — threat of new entry, supplier power, buyer power, threat of substitutes, competitive rivalry. Provide porter_five_forces_summary (brief) and porter_five_forces_detail (one sentence per force).
4. Competitive feature matrix: Build a grid of 4–6 main players × key features (e.g. personalization, condition-specific, clinician network, price tier). Summarize in feature_matrix_summary (text or structured).
5. 2×2 positioning map: Define positioning_2x2_axes (e.g. "Degree of specialization (low→high) vs Digital tooling depth" or "Price vs Feature breadth"); positioning_2x2_note describing where incumbents and a hypothetical wedge sit.
6. Battle cards for key players (e.g. Calm, Headspace, BetterHelp, Lyra for mental health): competitor_name, value_proposition, strengths, weaknesses, pricing, gtm_summary, key_features (list for feature matrix).

Output format (strict JSON, no markdown):
{{
  "category_name": "<category name>",
  "segment_name": "<segment name>",
  "delivery_mechanisms": ["<e.g. API>", "<e.g. SaaS>"],
  "product_feature_gaps": ["<gap1>", "<gap2>"],
  "experience_gaps": ["<gap1>", "<gap2>"],
  "moat_assessment": "<paragraph>",
  "notes": "<optional>",
  "porter_five_forces_summary": "<brief>",
  "porter_five_forces_detail": "<1 sentence per force: new entry, suppliers, buyers, substitutes, rivalry>",
  "competitive_matrix_note": "<e.g. 2x2 position>",
  "feature_matrix_summary": "<4-6 players × key features grid summary>",
  "positioning_2x2_axes": "<e.g. Level of specialization vs Digital tooling depth>",
  "positioning_2x2_note": "<where incumbents and wedge sit>",
  "battle_cards": [
    {{"competitor_name": "<name>", "value_proposition": "<vp>", "strengths": ["s1"], "weaknesses": ["w1"], "pricing": "<>", "gtm_summary": "<brief>", "key_features": ["f1","f2"]}}
  ]
}}
"""


def run(
    pain_points: PainPoints,
    model_name: str | None = None,
) -> CompetitionGaps:
    """
    Run Competitive Strategist for one segment (using its pain points).
    Returns CompetitionGaps for this segment.
    """
    model = model_name or get_model("competitive_strategist")
    prompt = PROMPT_TEMPLATE.format(
        category_name=pain_points.category_name,
        segment_name=pain_points.segment_name,
        zmot=pain_points.zero_moment_of_truth or "Not specified.",
        alternative_paths="; ".join(pain_points.alternative_paths) or "None specified.",
        retention_killers="; ".join(pain_points.retention_killers) or "None specified.",
    )
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    battle_cards = []
    for bc in data.get("battle_cards") or []:
        if isinstance(bc, dict):
            battle_cards.append(
                BattleCard(
                    competitor_name=bc.get("competitor_name") or "",
                    value_proposition=bc.get("value_proposition") or "",
                    strengths=_ensure_str_list(bc.get("strengths")),
                    weaknesses=_ensure_str_list(bc.get("weaknesses")),
                    pricing=bc.get("pricing") or "",
                    gtm_summary=bc.get("gtm_summary") or "",
                    key_features=_ensure_str_list(bc.get("key_features")),
                )
            )
    return CompetitionGaps(
        category_name=data.get("category_name") or pain_points.category_name,
        segment_name=data.get("segment_name") or pain_points.segment_name,
        delivery_mechanisms=_ensure_str_list(data.get("delivery_mechanisms")),
        product_feature_gaps=_ensure_str_list(data.get("product_feature_gaps")),
        experience_gaps=_ensure_str_list(data.get("experience_gaps")),
        moat_assessment=_to_str(data.get("moat_assessment")),
        notes=_to_str(data.get("notes")),
        porter_five_forces_summary=_to_str(data.get("porter_five_forces_summary")),
        porter_five_forces_detail=_to_str(data.get("porter_five_forces_detail")),
        competitive_matrix_note=_to_str(data.get("competitive_matrix_note")),
        feature_matrix_summary=_to_str(data.get("feature_matrix_summary")),
        positioning_2x2_axes=_to_str(data.get("positioning_2x2_axes")),
        positioning_2x2_note=_to_str(data.get("positioning_2x2_note")),
        battle_cards=battle_cards,
    )
