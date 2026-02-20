"""
Agent 3: Behavioral Ethologist.
Input: One segment (from Agent 2) + category name.
Output: Section 3 slice — ZMOT, alternative paths, retention killers.
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import PainPoints


SYSTEM = (
    "You are a Behavioral Ethologist in market research. You map the human/user element: "
    "when users realize they have a problem, what workarounds they use, and why they quit solutions. "
    "Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Analyze user behavior and pain points for this segment.

Category: {category_name}
Segment: {segment_name}
Segment context: {segment_context}

Research questions:
1. The 'Zero Moment of Truth': When exactly does the user realize their current process is broken? (Describe the trigger moment.)
2. Alternative Path Analysis: What are the 'free' or 'manual' workarounds users use before paying for a solution?
3. Retention Killers: Why do they quit existing solutions? (e.g., 'Too complex for my staff,' 'Data silo issues,' 'Hidden costs'.)

Output format (strict JSON, no markdown):
{{
  "category_name": "<category name>",
  "segment_name": "<segment name>",
  "zero_moment_of_truth": "<description of when user realizes the problem>",
  "alternative_paths": ["<workaround1>", "<workaround2>"],
  "retention_killers": ["<reason1>", "<reason2>"],
  "notes": "<optional>"
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

    return PainPoints(
        category_name=data.get("category_name") or category_name,
        segment_name=data.get("segment_name") or segment_name,
        zero_moment_of_truth=data.get("zero_moment_of_truth") or "",
        alternative_paths=list(data.get("alternative_paths") or []),
        retention_killers=list(data.get("retention_killers") or []),
        notes=data.get("notes") or "",
    )
