"""
Stage 0P: Problem Scoping (Problem-Driven Mode).
Input: User-provided problem statement, target user/segment, and validation questions.
Output: Problem Statement Brief (1–2 page equivalent).
"""
from __future__ import annotations

from src.config import get_model
from src.gemini_client import generate_json
from src.models import Stage0POutput


SYSTEM = (
    "You are a market research expert focused on problem validation. You turn raw problem statements "
    "and validation answers into a structured Problem Statement Brief: problem definition, affected users, "
    "current spend, existing solutions, and hypotheses. Respond with valid JSON only."
)

PROMPT_TEMPLATE = """
Create a Problem Statement Brief from the following inputs (Problem-Driven research).

Industry/Area: {industry}

Problem statement (user): {problem_statement}

Target user: {target_user}
Target segment: {target_segment}

Validation inputs (expand and structure these into the brief):
- Market Money: {market_money}
- User Behavior: {user_behavior}
- Competition: {competition}
- AI Advantage: {ai_advantage}

Hypotheses to validate (user): {hypotheses}

Produce a structured brief. Output format (strict JSON, no markdown):
{{
  "problem_statement": "<refined 1–2 paragraph problem definition>",
  "target_user": "<who is affected>",
  "target_segment": "<target segment>",
  "market_money": "<where money is spent; budget line; who is incentivized>",
  "user_behavior": "<when pain occurs; what users try first; why solutions fail>",
  "competition": "<good enough incumbents; why people still complain>",
  "ai_advantage": "<expensive/slow/inconsistent human effort; repetitive high-impact decisions>",
  "hypotheses": ["<hypothesis1>", "<hypothesis2>"],
  "summary": "<2–3 sentence executive summary of the problem and opportunity>"
}}
"""


def run(
    industry: str,
    problem_statement: str,
    target_user: str = "",
    target_segment: str = "",
    market_money: str = "",
    user_behavior: str = "",
    competition: str = "",
    ai_advantage: str = "",
    hypotheses: list[str] | None = None,
    model_name: str | None = None,
) -> Stage0POutput:
    """
    Run Problem Scoper (Stage 0P) for problem-driven mode.
    Returns Stage0POutput (problem statement brief).
    """
    model = model_name or get_model("problem_scoper")
    hyp_list = hypotheses or []
    hyp_str = "\n".join(f"- {h}" for h in hyp_list) if hyp_list else "None provided."
    prompt = PROMPT_TEMPLATE.format(
        industry=industry.strip(),
        problem_statement=(problem_statement or "Not provided.").strip(),
        target_user=(target_user or "Not specified.").strip(),
        target_segment=(target_segment or "Not specified.").strip(),
        market_money=(market_money or "Not provided.").strip(),
        user_behavior=(user_behavior or "Not provided.").strip(),
        competition=(competition or "Not provided.").strip(),
        ai_advantage=(ai_advantage or "Not provided.").strip(),
        hypotheses=hyp_str,
    )
    data = generate_json(prompt, model, system_instruction=SYSTEM)

    raw_hyps = data.get("hypotheses")
    if isinstance(raw_hyps, list):
        hyp_out = [str(h) for h in raw_hyps]
    else:
        hyp_out = hyp_list

    return Stage0POutput(
        problem_statement=data.get("problem_statement") or "",
        target_user=data.get("target_user") or target_user,
        target_segment=data.get("target_segment") or target_segment,
        market_money=data.get("market_money") or "",
        user_behavior=data.get("user_behavior") or "",
        competition=data.get("competition") or "",
        ai_advantage=data.get("ai_advantage") or "",
        hypotheses=hyp_out,
        summary=data.get("summary") or "",
    )
