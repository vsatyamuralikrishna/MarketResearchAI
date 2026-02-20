"""
Agent 2: Segment Specialist.
Input: One category from Agent 1 + optional short industry summary.
Output: Section 2 slice — primary/secondary segments, growth drivers, under/over-capitalization.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import CategorySegments, Segment


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
2. What are the Growth Drivers (e.g., regulatory shifts, tech breakthroughs) for each segment?
3. Which segments are currently Under-capitalized vs. Over-saturated?

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
      "notes": "<optional notes>"
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
            segments.append(
                Segment(
                    name=s.get("name") or "Unnamed",
                    segment_type=s.get("segment_type") or "primary",
                    description=s.get("description") or "",
                    growth_drivers=list(s.get("growth_drivers") or []),
                    under_capitalized=bool(s.get("under_capitalized")),
                    over_saturated=bool(s.get("over_saturated")),
                    notes=s.get("notes") or "",
                )
            )
        elif isinstance(s, str):
            segments.append(Segment(name=s))

    return CategorySegments(category_name=cat_name, segments=segments)
