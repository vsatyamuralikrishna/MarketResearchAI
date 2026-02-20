"""
Agent 4: Competitive Strategist.
Input: Same segment + pain points (Section 3 slice).
Output: Section 4 slice — delivery mechanism, gaps, moat assessment.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import CompetitionGaps, PainPoints


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
1. Delivery Mechanism Audit: Is the solution currently delivered via API, Managed Service, Mobile App, or SaaS? List all that apply.
2. Gap Identification: Where are the 'Product Feature Gaps' vs. 'Experience Gaps'?
3. The 'Moat' Assessment: Are existing players protected by brand, network effects, or high switching costs? Summarize.

Output format (strict JSON, no markdown):
{{
  "category_name": "<category name>",
  "segment_name": "<segment name>",
  "delivery_mechanisms": ["<e.g. API>", "<e.g. SaaS>"],
  "product_feature_gaps": ["<gap1>", "<gap2>"],
  "experience_gaps": ["<gap1>", "<gap2>"],
  "moat_assessment": "<paragraph on incumbents' moats>",
  "notes": "<optional>"
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

    return CompetitionGaps(
        category_name=data.get("category_name") or pain_points.category_name,
        segment_name=data.get("segment_name") or pain_points.segment_name,
        delivery_mechanisms=list(data.get("delivery_mechanisms") or []),
        product_feature_gaps=list(data.get("product_feature_gaps") or []),
        experience_gaps=list(data.get("experience_gaps") or []),
        moat_assessment=data.get("moat_assessment") or "",
        notes=data.get("notes") or "",
    )
