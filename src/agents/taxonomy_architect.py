"""
Agent 1: Taxonomy Architect.
Input: High-level industry/area.
Output: Section 1 — categories with TAM/SOM, CAGRs (2024–2030), trends.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import Category, Section1


SYSTEM = (
    "You are a market research Taxonomy Architect. You decompose industries into "
    "logical categories and provide TAM/SOM and CAGR data. Always respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Analyze the following industry/area and produce a decomposition tree (categories) with market metrics.

Industry/Area: {industry}

Answer these research questions and output a single JSON object:
1. What are the core technical or service-based Categories in this industry? (List 3–7 categories.)
2. For each category: What is the Total Addressable Market (TAM) vs. Serviceable Obtainable Market (SOM)? Use concise text (e.g. "$50B / $5B").
3. For each category: What is the Historical CAGR and Projected CAGR (2024–2030)? Use percentage strings (e.g. "8%", "12%").
4. Which categories show the highest Historical CAGR vs. Projected CAGR? Reflect this in your trends.
5. What are the core market trends for each category?

Output format (strict JSON, no markdown):
{{
  "industry": "<industry name>",
  "summary": "<2–3 sentence executive summary of the industry and key metrics>",
  "categories": [
    {{
      "name": "<category name>",
      "description": "<short description>",
      "tam": "<TAM estimate>",
      "som": "<SOM estimate>",
      "historical_cagr": "<e.g. 8%>",
      "projected_cagr": "<e.g. 12%>",
      "trends": ["<trend1>", "<trend2>"]
    }}
  ]
}}
"""


def run(industry: str, model_name: str | None = None) -> Section1:
    """
    Run Taxonomy Architect on the given industry.
    Returns Section1 (categories, market cap, trends).
    """
    model = model_name or get_model("taxonomy")
    prompt = PROMPT_TEMPLATE.format(industry=industry.strip())
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    industry_str = data.get("industry") or industry
    summary = data.get("summary") or ""
    raw_cats = data.get("categories") or []
    categories = []
    for c in raw_cats:
        if isinstance(c, dict):
            categories.append(
                Category(
                    name=c.get("name") or "Unnamed",
                    description=c.get("description") or "",
                    tam=c.get("tam") or "",
                    som=c.get("som") or "",
                    historical_cagr=c.get("historical_cagr") or "",
                    projected_cagr=c.get("projected_cagr") or "",
                    trends=list(c.get("trends") or []),
                )
            )
        elif isinstance(c, str):
            categories.append(Category(name=c))

    return Section1(industry=industry_str, summary=summary, categories=categories)
