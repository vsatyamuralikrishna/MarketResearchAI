"""
Stage 0E: Industry Scoping & Category Taxonomy (Exploratory Mode).
Builds 4-level hierarchy: Industry → Category → Subcategory → Segment.
Output: Industry Taxonomy Map with preliminary size signals.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import (
    Stage0EOutput,
    TaxonomyCategory,
    TaxonomySegment,
    TaxonomySubcategory,
)


SYSTEM = (
    "You are a market research expert building industry taxonomies. You map the entire industry "
    "into a structured 4-level hierarchy (Industry → Category → Subcategory → Segment) following "
    "market mapping methodology. Use analyst-style categories where applicable. Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Build an Industry Taxonomy Map for the following industry/area.

Industry/Area: {industry}
{extra_context}

Answer:
1. Industry boundaries: What is the broadest definition? What adjacent industries overlap?
2. Value chain: Who produces, distributes, delivers, and consumes?
3. Categories (Level 2): What are the major categories? (e.g. 3–6 categories; align with how Gartner/McKinsey/Deloitte segment where relevant.)
4. For each category: Subcategories (Level 3) and Segments (Level 4). Differentiate by modality, customer type, geography, or technology.
5. For each category/segment: preliminary size range (<$1B, $1-10B, $10-50B, $50B+) and growth signal (emerging | growing | mature | declining).

Output format (strict JSON, no markdown):
{{
  "industry": "<industry name>",
  "industry_boundaries": "<1–2 paragraphs>",
  "value_chain_summary": "<1 paragraph>",
  "summary": "<2–3 sentence executive summary>",
  "categories": [
    {{
      "name": "<category name>",
      "description": "<short description>",
      "size_range": "<e.g. $10-50B>",
      "growth_signal": "emerging|growing|mature|declining",
      "subcategories": [
        {{
          "name": "<subcategory name>",
          "description": "<short description>",
          "segments": [
            {{
              "name": "<segment name>",
              "description": "<short description>",
              "key_players_initial": ["<player1>", "<player2>"],
              "size_range": "<e.g. $1-10B>",
              "growth_signal": "emerging|growing|mature|declining"
            }}
          ]
        }}
      ]
    }}
  ]
}}
"""


def run(
    industry: str,
    industry_boundaries_hint: str = "",
    model_name: str | None = None,
) -> Stage0EOutput:
    """
    Run Industry Scoper (Stage 0E) for exploratory mode.
    Returns Stage0EOutput (taxonomy map).
    """
    extra = f"Optional context from user: {industry_boundaries_hint}" if industry_boundaries_hint else ""
    prompt = PROMPT_TEMPLATE.format(industry=industry.strip(), extra_context=extra)
    model = model_name or get_model("industry_scoper")
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    industry_str = data.get("industry") or industry
    categories_out = []
    for c in data.get("categories") or []:
        if not isinstance(c, dict):
            continue
        subcats = []
        for sc in c.get("subcategories") or []:
            if not isinstance(sc, dict):
                continue
            segs = []
            for s in sc.get("segments") or []:
                if isinstance(s, dict):
                    segs.append(
                        TaxonomySegment(
                            name=s.get("name") or "Unnamed",
                            description=s.get("description") or "",
                            key_players_initial=list(s.get("key_players_initial") or []),
                            size_range=s.get("size_range") or "",
                            growth_signal=s.get("growth_signal") or "",
                        )
                    )
            subcats.append(
                TaxonomySubcategory(
                    name=sc.get("name") or "Unnamed",
                    description=sc.get("description") or "",
                    segments=segs,
                )
            )
        categories_out.append(
            TaxonomyCategory(
                name=c.get("name") or "Unnamed",
                description=c.get("description") or "",
                subcategories=subcats,
                size_range=c.get("size_range") or "",
                growth_signal=c.get("growth_signal") or "",
            )
        )

    return Stage0EOutput(
        industry=industry_str,
        industry_boundaries=data.get("industry_boundaries") or "",
        value_chain_summary=data.get("value_chain_summary") or "",
        categories=categories_out,
        summary=data.get("summary") or "",
    )
