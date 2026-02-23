"""
Agent 2: Segment Specialist.
Input: One category from Agent 1 + optional short industry summary.
Output: Section 2 slice — primary/secondary segments, growth drivers, under/over-capitalization.
"""
from __future__ import annotations

from typing import Any

from src.config import get_model
from src.gemini_client import generate_json
from src.models import CategorySegments, Segment, SegmentPlayer


def _ensure_str_list(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    if isinstance(x, str):
        return [x] if x.strip() else []
    return []


SYSTEM = (
    "You are a market research Segment Specialist. You drill down into categories "
    "to identify niche segments, growth drivers, and capital saturation. Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Analyze the following category and identify its segments.

Industry summary (brief): {industry_summary}

Category: {category_name}
Category context: {category_context}

Research questions:
1. For this category, what are the Primary vs. Secondary Segments? (List 2–5 segments; label each as "primary" or "secondary".)
2. What are the Growth Drivers for each segment?
3. Which segments are Under-capitalized vs. Over-saturated?
4. (Segment deep-dive) For each segment provide a segment profile block: top 3–5 players with market_share (e.g. 25%) and market_share_band (e.g. "top 3 control 60–70%"), business_model, pricing_note; typical pricing_range for segment; technology_stack; regulatory_requirements (HIPAA, state licensure, FDA for PDTs, etc.); funding_landscape; num_players_estimate (e.g. "15-20"); concentration_band (fragmented | moderate | concentrated) and hhi_note; one-line segment_deep_dive_summary for a matrix row (size, CAGR, # players, concentration, business model, pricing band).

Output format (strict JSON, no markdown):
{{
  "category_name": "<category name>",
  "segments": [
    {{
      "name": "<segment name>",
      "segment_type": "primary or secondary",
      "description": "<short description>",
      "growth_drivers": ["<driver1>", "<driver2>"],
      "under_capitalized": true or false,
      "over_saturated": true or false,
      "notes": "<optional>",
      "top_players": [{{"name": "<player>", "market_share": "<e.g. 25%>", "market_share_band": "<e.g. top 3 control 60-70%>", "business_model": "<e.g. D2C subscription>", "pricing_note": "<e.g. $15/mo>"}}],
      "pricing_range": "<e.g. $10-50/mo>",
      "technology_stack": "<dominant tech/delivery>",
      "regulatory_requirements": "<brief>",
      "funding_landscape": "<total VC, recent rounds>",
      "hhi_note": "<concentration note>",
      "num_players_estimate": "<e.g. 15-20>",
      "concentration_band": "fragmented|moderate|concentrated",
      "segment_deep_dive_summary": "<one-line: size, CAGR, # players, concentration, business model, pricing>"
    }}
  ]
}}
"""


def run(
    category_name: str,
    industry_summary: str = "",
    category_context: str = "",
    model_name: str | None = None,
) -> CategorySegments:
    """
    Run Segment Specialist for one category.
    Returns CategorySegments (segments for this category).
    """
    model = model_name or get_model("segment_specialist")
    prompt = PROMPT_TEMPLATE.format(
        industry_summary=industry_summary or "Not provided.",
        category_name=category_name,
        category_context=category_context or "No additional context.",
    )
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    cat_name = data.get("category_name") or category_name
    raw_segments = data.get("segments") or []
    segments = []
    for s in raw_segments:
        if isinstance(s, dict):
            players = []
            for p in s.get("top_players") or []:
                if isinstance(p, dict):
                    players.append(
                        SegmentPlayer(
                            name=p.get("name") or "",
                            market_share=p.get("market_share") or "",
                            market_share_band=p.get("market_share_band") or "",
                            business_model=p.get("business_model") or "",
                            pricing_note=p.get("pricing_note") or "",
                        )
                    )
            segments.append(
                Segment(
                    name=s.get("name") or "Unnamed",
                    segment_type=s.get("segment_type") or "primary",
                    description=s.get("description") or "",
                    growth_drivers=_ensure_str_list(s.get("growth_drivers")),
                    under_capitalized=bool(s.get("under_capitalized")),
                    over_saturated=bool(s.get("over_saturated")),
                    notes=s.get("notes") or "",
                    top_players=players,
                    pricing_range=s.get("pricing_range") or "",
                    technology_stack=s.get("technology_stack") or "",
                    regulatory_requirements=s.get("regulatory_requirements") or "",
                    funding_landscape=s.get("funding_landscape") or "",
                    hhi_note=s.get("hhi_note") or "",
                    num_players_estimate=s.get("num_players_estimate") or "",
                    concentration_band=s.get("concentration_band") or "",
                    segment_deep_dive_summary=s.get("segment_deep_dive_summary") or "",
                )
            )
        elif isinstance(s, str):
            segments.append(Segment(name=s))

    return CategorySegments(category_name=cat_name, segments=segments)
