"""
Stage 1: Market Sizing & Opportunity Assessment (Both Modes).
Exploratory: Category × Segment sizing matrix with CAGR.
Problem-Driven: TAM → SAM → SOM funnel with assumptions.
"""
from __future__ import annotations

from typing import Any

from src.config import get_model
from src.gemini_client import generate_json
from src.models import (
    CategorySizingRow,
    Stage1Output,
    TAMSAMSOM,
)


def _ensure_str_list(x: Any) -> list[str]:
    """Coerce to list of strings; LLM sometimes returns a single string for list fields."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    if isinstance(x, str):
        return [x] if x.strip() else []
    return []


SYSTEM = (
    "You are a market sizing expert. You produce either (a) a category-level sizing matrix with "
    "CAGR for exploratory research, or (b) a TAM-SAM-SOM funnel with assumptions for problem-driven "
    "research. Use realistic ranges and cite approach (top-down/bottom-up). Respond with valid JSON only."
)

PROMPT_EXPLORATORY = """
Produce a Market Sizing matrix for this industry (Exploratory mode). Fill every column; no blank CAGRs or sizes.

Industry: {industry}
Summary / context: {context}

Categories (and optional segments) to size:
{categories_text}

For each category produce a complete matrix row:
- category_name, market_size (e.g. $50B), historical_cagr and projected_cagr (e.g. 8%, 12%), largest_segment_name, largest_segment_size, segment_cagr, growth_signal (emerging|growing|mature|declining).
- key_segments: list of 2–5 segment names in this category.
- growth_drivers: 3–4 bullets (e.g. "Employer demand for scalable benefits", "Telehealth parity laws").
- headwinds: 3–4 bullets (e.g. "Reimbursement uncertainty for PDTs", "Therapist supply constraints").

Also output mode_clarification: "Stage 1 Exploratory: we estimate TAM per category and segment; SAM/SOM are not modeled in this mode."

Output format (strict JSON, no markdown):
{{
  "mode": "exploratory",
  "mode_clarification": "Stage 1 Exploratory: TAM per category/segment; SAM/SOM not modeled.",
  "summary": "<2–3 sentence summary>",
  "category_sizing_matrix": [
    {{
      "category_name": "<name>",
      "market_size": "<e.g. $50B>",
      "historical_cagr": "<e.g. 8%>",
      "projected_cagr": "<e.g. 12%>",
      "largest_segment_name": "<name>",
      "largest_segment_size": "<e.g. $20B>",
      "segment_cagr": "<e.g. 12%>",
      "growth_signal": "emerging|growing|mature|declining",
      "key_segments": ["<seg1>", "<seg2>"],
      "growth_drivers": ["<driver1>", "<driver2>", "<driver3>"],
      "headwinds": ["<headwind1>", "<headwind2>"]
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
  "mode_clarification": "Stage 1 Problem-Driven: full TAM-SAM-SOM funnel with assumptions.",
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
                    historical_cagr=row.get("historical_cagr") or row.get("cagr") or "",
                    projected_cagr=row.get("projected_cagr") or "",
                    largest_segment_name=row.get("largest_segment_name") or "",
                    largest_segment_size=row.get("largest_segment_size") or "",
                    segment_cagr=row.get("segment_cagr") or "",
                    growth_signal=row.get("growth_signal") or "",
                    key_segments=_ensure_str_list(row.get("key_segments")),
                    growth_drivers=_ensure_str_list(row.get("growth_drivers")),
                    headwinds=_ensure_str_list(row.get("headwinds")),
                )
            )
    return Stage1Output(
        mode="exploratory",
        mode_clarification=data.get("mode_clarification") or "Stage 1 Exploratory: TAM per category/segment; SAM/SOM not modeled.",
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
        mode_clarification=data.get("mode_clarification") or "Stage 1 Problem-Driven: full TAM-SAM-SOM funnel.",
        category_sizing_matrix=[],
        tam_sam_som=tam_sam_som,
        summary=data.get("summary") or "",
    )
