"""
Agent 3: Behavioral Ethologist.
Input: One segment (from Agent 2) + category name.
Output: Section 3 slice — ZMOT, alternative paths, retention killers.
"""
from __future__ import annotations

from typing import Any

from src.config import get_model
from src.gemini_client import generate_json
from src.models import PainPoints, PersonaCard


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
    "You are a Behavioral Ethologist in market research. You map the human/user element: "
    "ZMOT, workarounds, retention killers; personas with JTBD and WTP; demand signals; customer journey. "
    "Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Analyze user behavior and pain points for this segment.

Category: {category_name}
Segment: {segment_name}
Segment context: {segment_context}

Research questions:
1. Zero Moment of Truth: When does the user realize their process is broken?
2. Alternative paths: What workarounds do users try before paying?
3. Retention killers: Why do they quit existing solutions?
4. Persona cards: For each key persona (e.g. "College Student with Social Anxiety", "New grad with burnout") provide: name, demographics, jobs_to_be_done (list), triggers, willingness_to_pay_range, preferred_channels (how they find solutions).
5. Demand signals: Search trend direction, review volumes for relevant apps, any public conversion/churn evidence (even estimated).
6. Customer journey: Map ZMOT → alternative paths → retention killers into a short textual journey: trigger → search → trial → adoption → churn.

Output format (strict JSON, no markdown):
{{
  "category_name": "<category name>",
  "segment_name": "<segment name>",
  "zero_moment_of_truth": "<description>",
  "alternative_paths": ["<workaround1>", "<workaround2>"],
  "retention_killers": ["<reason1>", "<reason2>"],
  "notes": "<optional>",
  "persona_summary": "<who are end users; primary needs>",
  "persona_cards": [
    {{"name": "<persona name>", "demographics": "<>", "jobs_to_be_done": ["j1","j2"], "triggers": "<>", "willingness_to_pay_range": "<>", "preferred_channels": "<>", "notes": ""}}
  ],
  "jobs_to_be_done": ["<job1>", "<job2>"],
  "demand_signals": "<search trends, forum activity, review volume, conversion/churn if available>",
  "willingness_to_pay": "<evidence or range>",
  "customer_journey_summary": "<trigger → search → trial → adoption → churn (2-4 sentences)>"
}}
"""


def run(
    category_name: str,
    segment_name: str,
    segment_context: str = "",
    model_name: str | None = None,
) -> PainPoints:
    """
    Run Behavioral Ethologist for one segment.
    Returns PainPoints for this segment.
    """
    model = model_name or get_model("behavioral_ethologist")
    prompt = PROMPT_TEMPLATE.format(
        category_name=category_name,
        segment_name=segment_name,
        segment_context=segment_context or "No additional context.",
    )
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    persona_cards = []
    for pc in data.get("persona_cards") or []:
        if isinstance(pc, dict):
            persona_cards.append(
                PersonaCard(
                    name=pc.get("name") or "",
                    demographics=pc.get("demographics") or "",
                    jobs_to_be_done=_ensure_str_list(pc.get("jobs_to_be_done")),
                    triggers=pc.get("triggers") or "",
                    willingness_to_pay_range=pc.get("willingness_to_pay_range") or "",
                    preferred_channels=pc.get("preferred_channels") or "",
                    notes=pc.get("notes") or "",
                )
            )
    return PainPoints(
        category_name=data.get("category_name") or category_name,
        segment_name=data.get("segment_name") or segment_name,
        zero_moment_of_truth=data.get("zero_moment_of_truth") or "",
        alternative_paths=_ensure_str_list(data.get("alternative_paths")),
        retention_killers=_ensure_str_list(data.get("retention_killers")),
        notes=data.get("notes") or "",
        persona_summary=data.get("persona_summary") or "",
        persona_cards=persona_cards,
        jobs_to_be_done=_ensure_str_list(data.get("jobs_to_be_done")),
        demand_signals=data.get("demand_signals") or "",
        willingness_to_pay=data.get("willingness_to_pay") or "",
        customer_journey_summary=data.get("customer_journey_summary") or "",
    )
