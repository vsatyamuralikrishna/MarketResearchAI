"""
Stage 0E: Industry Scoping & Category Taxonomy (Exploratory Mode).
Builds 4-level hierarchy: Industry → Category → Subcategory → Segment.
Output: Industry Taxonomy Map with preliminary size signals.
Optional: use Gemini Deep Research for web-backed, cited insights.
"""
from __future__ import annotations

from typing import Any, Callable

from src.config import get_model, get_use_deep_research
from src.deep_research_client import generate_json_via_deep_research
from src.gemini_client import generate_json
from src.models import (
    Stage0EOutput,
    TaxonomyCategory,
    TaxonomyQuantification,
    TaxonomySegment,
    TaxonomySubcategory,
)


SYSTEM = (
    "You are a market research expert building industry taxonomies. You map the entire industry "
    "into a structured 4-level hierarchy (Industry → Category → Subcategory → Segment). "
    "Produce a formal Industry Taxonomy Map deliverable with explicit counts, PESTEL, and classification. "
    "Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Build an Industry Taxonomy Map for the following industry/area. Deliver a formal 4-level artifact.

Industry/Area: {industry}
{extra_context}

Required outputs:

1. **Level 1**: Explicit industry name (e.g. "Youth & Young Adult Mental Health Solutions" or the given industry).

2. **Industry boundaries**: Broadest definition; demographics if relevant; solution types (e.g. digital-first, tech-enabled in-person); core purpose. List adjacent industries that overlap.

3. **Value chain**: Producers → Distributors/Aggregators → Delivery channels → Consumers, with concrete examples per layer.

4. **Industry classification**: How is this space classified? (e.g. NAICS codes if applicable; how Gartner/McKinsey/Deloitte segment it; trade associations.)

5. **PESTEL overview** (half-page): Political/regulatory (e.g. telehealth parity, PDT regulation); Economic; Sociocultural (e.g. stigma reduction, TikTok/Instagram as awareness channels); Technological; Environmental if relevant; Legal. Tailor to the industry (e.g. youth mental health: rising stigma reduction, regulation on telehealth and PDTs).

6. **4-level taxonomy**:
   - Level 2: 3–6 Categories (major categories).
   - Level 3: Subcategories under each (e.g. under "Digital Therapeutics & Self-Care": content-led wellness, PDTs, condition-specific self-help).
   - Level 4: Specific segments (e.g. "AI conversational companions for anxiety in Gen Z"). Each with key_players_initial, size_range (<$1B, $1-10B, $10-50B, $50B+), growth_signal (emerging|growing|mature|declining).

7. **Taxonomy quantification** (at end): Explicit counts — "Categories identified: N; Segments mapped: M"; category size orders of magnitude; growth signal tags per category (e.g. "3 growing, 2 emerging").

Output format (strict JSON, no markdown):
{{
  "industry": "<industry name>",
  "level1_industry_name": "<explicit Level 1 for taxonomy table>",
  "industry_boundaries": "<1–2 paragraphs>",
  "value_chain_summary": "<1 paragraph with layers>",
  "industry_classification": "<NAICS, analyst classifications, trade bodies>",
  "pestel_overview": "<half-page: regulatory, economic, tech, sociocultural drivers>",
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
  ],
  "taxonomy_quantification": {{
    "categories_count": 5,
    "segments_count": 12,
    "size_orders_summary": "<e.g. Category A: $10-50B; Category B: $1-10B>",
    "growth_signals_summary": "<e.g. 3 growing, 2 emerging, 1 mature>"
  }}
}}
"""


def _ensure_str_list(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    if isinstance(x, str):
        return [x] if x.strip() else []
    return []


def run(
    industry: str,
    industry_boundaries_hint: str = "",
    model_name: str | None = None,
    use_deep_research: bool | None = None,
    progress_callback: Callable[[str, float], None] | None = None,
) -> Stage0EOutput:
    """
    Run Industry Scoper (Stage 0E) for exploratory mode.
    When use_deep_research is True, uses Gemini Deep Research Agent (web search, slower, cited).
    Returns Stage0EOutput (taxonomy map).
    """
    extra = f"Optional context from user: {industry_boundaries_hint}" if industry_boundaries_hint else ""
    prompt = PROMPT_TEMPLATE.format(industry=industry.strip(), extra_context=extra)
    use_dr = use_deep_research if use_deep_research is not None else get_use_deep_research()
    if use_dr:
        data = generate_json_via_deep_research(
            prompt,
            system_instruction=SYSTEM,
            progress_callback=progress_callback,
            json_instruction="After your research, output a single valid JSON object with the exact keys shown above (industry, level1_industry_name, industry_boundaries, value_chain_summary, industry_classification, pestel_overview, summary, categories, taxonomy_quantification). No markdown, no code fence.",
        )
    else:
        model = model_name or get_model("industry_scoper")
        data = generate_json(prompt, model, system_instruction=SYSTEM)

    industry_str = data.get("industry") or industry
    level1 = data.get("level1_industry_name") or industry_str
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
                            key_players_initial=_ensure_str_list(s.get("key_players_initial")),
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

    tq = data.get("taxonomy_quantification")
    if isinstance(tq, dict):
        quant = TaxonomyQuantification(
            categories_count=int(tq.get("categories_count") or 0),
            segments_count=int(tq.get("segments_count") or 0),
            size_orders_summary=(tq.get("size_orders_summary") or "").strip(),
            growth_signals_summary=(tq.get("growth_signals_summary") or "").strip(),
        )
    else:
        quant = TaxonomyQuantification(
            categories_count=len(categories_out),
            segments_count=sum(len(sc.segments) for tc in categories_out for sc in tc.subcategories),
        )

    return Stage0EOutput(
        industry=industry_str,
        level1_industry_name=level1,
        industry_boundaries=data.get("industry_boundaries") or "",
        value_chain_summary=data.get("value_chain_summary") or "",
        industry_classification=data.get("industry_classification") or "",
        pestel_overview=data.get("pestel_overview") or "",
        categories=categories_out,
        taxonomy_quantification=quant,
        summary=data.get("summary") or "",
    )
