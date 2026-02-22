"""
Stage 1: Market Sizing & Opportunity Assessment (Both Modes).
Exploratory: Category × Segment sizing matrix with CAGR.
Problem-Driven: TAM → SAM → SOM funnel with assumptions.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import (
    CategorySizingRow,
    Stage1Output,
    TAMSAMSOM,
)


SYSTEM = (
    "You are a market sizing expert. You produce either (a) a category-level sizing matrix with "
    "CAGR for exploratory research, or (b) a TAM-SAM-SOM funnel with assumptions for problem-driven "
    "research. Use realistic ranges and cite approach (top-down/bottom-up). Respond with valid JSON only."
)

PROMPT_EXPLORATORY = """
Produce a Market Sizing matrix for this industry (Exploratory mode).

Industry: {industry}
Summary / context: {context}

Categories (and optional segments) to size:
{categories_text}

For each category produce: market size (e.g. $X.XB), CAGR (e.g. X%), largest segment name, largest segment size, segment CAGR.
Identify growth drivers and headwinds. Output format (strict JSON, no markdown):
{{
  "mode": "exploratory",
  "summary": "<2–3 sentence summary of market size and growth>",
  "category_sizing_matrix": [
    {{
      "category_name": "<name>",
      "market_size": "<e.g. $50B>",
      "cagr": "<e.g. 8%>",
      "largest_segment_name": "<name>",
      "largest_segment_size": "<e.g. $20B>",
      "segment_cagr": "<e.g. 12%>"
    }}
  ]
}}
"""

PROMPT_PROBLEM_DRIVEN = """
Produce a TAM-SAM-SOM funnel for this specific opportunity (Problem-Driven mode).

Industry: {industry}
Problem / opportunity: {problem_summary}
Target user: {target_user}
Target segment: {target_segment}

Category context: {categories_text}

Define:
- TAM (Total Addressable Market): total potential customers × avg revenue per customer or top-down equivalent.
- SAM (Serviceable Addressable Market): TAM × % serviceable (geography, product fit, channel).
- SOM (Serviceable Obtainable Market): SAM × realistic capture rate.
Include assumptions and growth forecast. Output format (strict JSON, no markdown):
{{
  "mode": "problem_driven",
  "summary": "<2–3 sentence summary>",
  "tam_sam_som": {{
    "tam": "<value and brief rationale>",
    "sam": "<value and brief rationale>",
    "som": "<value and brief rationale>",
    "assumptions": "<key assumptions>",
    "growth_forecast": "<e.g. 3–5 year outlook>"
  }}
}}
"""


def _categories_to_text(categories: list[dict]) -> str:
    """Turn list of category dicts (from section1 or stage0e) into prompt text."""
    lines = []
    for c in categories:
        name = c.get("name") or "Unnamed"
        desc = c.get("description") or ""
        subcats = c.get("subcategories") or []
        if subcats:
            for sc in subcats:
                sc_name = sc.get("name") or ""
                segs = sc.get("segments") or []
                seg_names = [s.get("name") for s in segs if isinstance(s, dict) and s.get("name")]
                lines.append(f"- {name} > {sc_name}: segments {', '.join(seg_names) or 'N/A'}")
        else:
            lines.append(f"- {name}: {desc}")
    return "\n".join(lines) if lines else "No categories provided."


def run_exploratory(
    industry: str,
    context: str,
    categories: list[dict],
    model_name: str | None = None,
) -> Stage1Output:
    """Run Stage 1 in exploratory mode: category × segment sizing matrix."""
    model = model_name or get_model("market_sizing")
    categories_text = _categories_to_text(categories)
    prompt = PROMPT_EXPLORATORY.format(
        industry=industry,
        context=context or "No additional context.",
        categories_text=categories_text,
    )
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    matrix = []
    for row in data.get("category_sizing_matrix") or []:
        if isinstance(row, dict):
            matrix.append(
                CategorySizingRow(
                    category_name=row.get("category_name") or "",
                    market_size=row.get("market_size") or "",
                    cagr=row.get("cagr") or "",
                    largest_segment_name=row.get("largest_segment_name") or "",
                    largest_segment_size=row.get("largest_segment_size") or "",
                    segment_cagr=row.get("segment_cagr") or "",
                )
            )
    return Stage1Output(
        mode="exploratory",
        category_sizing_matrix=matrix,
        tam_sam_som=None,
        summary=data.get("summary") or "",
    )


def run_problem_driven(
    industry: str,
    problem_summary: str,
    target_user: str,
    target_segment: str,
    categories: list[dict],
    model_name: str | None = None,
) -> Stage1Output:
    """Run Stage 1 in problem-driven mode: TAM-SAM-SOM funnel."""
    model = model_name or get_model("market_sizing")
    categories_text = _categories_to_text(categories)
    prompt = PROMPT_PROBLEM_DRIVEN.format(
        industry=industry,
        problem_summary=problem_summary or "Not provided.",
        target_user=target_user or "Not specified.",
        target_segment=target_segment or "Not specified.",
        categories_text=categories_text,
    )
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    tss = data.get("tam_sam_som")
    if isinstance(tss, dict):
        tam_sam_som = TAMSAMSOM(
            tam=tss.get("tam") or "",
            sam=tss.get("sam") or "",
            som=tss.get("som") or "",
            assumptions=tss.get("assumptions") or "",
            growth_forecast=tss.get("growth_forecast") or "",
        )
    else:
        tam_sam_som = None

    return Stage1Output(
        mode="problem_driven",
        category_sizing_matrix=[],
        tam_sam_som=tam_sam_som,
        summary=data.get("summary") or "",
    )
