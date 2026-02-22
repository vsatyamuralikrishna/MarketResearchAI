"""
Agent 4: Competitive Strategist.
Input: Same segment + pain points (Section 3 slice).
Output: Section 4 slice — delivery mechanism, gaps, moat assessment.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import BattleCard, CompetitionGaps, PainPoints


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
2. Product feature gaps vs. experience gaps.
3. Moat assessment: brand, network effects, switching costs.
4. (Competitive landscape) Porter's Five Forces summary for this segment; competitive matrix note (e.g. price vs. feature); if problem-driven, 1–3 battle cards: competitor name, value prop, strengths, weaknesses, GTM summary.

Output format (strict JSON, no markdown):
{{
  "category_name": "<category name>",
  "segment_name": "<segment name>",
  "delivery_mechanisms": ["<e.g. API>", "<e.g. SaaS>"],
  "product_feature_gaps": ["<gap1>", "<gap2>"],
  "experience_gaps": ["<gap1>", "<gap2>"],
  "moat_assessment": "<paragraph>",
  "notes": "<optional>",
  "porter_five_forces_summary": "<brief Porter summary>",
  "competitive_matrix_note": "<e.g. 2x2 position>",
  "battle_cards": [
    {{"competitor_name": "<name>", "value_proposition": "<vp>", "strengths": ["s1"], "weaknesses": ["w1"], "gtm_summary": "<brief>"}}
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
                    strengths=list(bc.get("strengths") or []),
                    weaknesses=list(bc.get("weaknesses") or []),
                    gtm_summary=bc.get("gtm_summary") or "",
                )
            )
    return CompetitionGaps(
        category_name=data.get("category_name") or pain_points.category_name,
        segment_name=data.get("segment_name") or pain_points.segment_name,
        delivery_mechanisms=list(data.get("delivery_mechanisms") or []),
        product_feature_gaps=list(data.get("product_feature_gaps") or []),
        experience_gaps=list(data.get("experience_gaps") or []),
        moat_assessment=data.get("moat_assessment") or "",
        notes=data.get("notes") or "",
        porter_five_forces_summary=data.get("porter_five_forces_summary") or "",
        competitive_matrix_note=data.get("competitive_matrix_note") or "",
        battle_cards=battle_cards,
    )
