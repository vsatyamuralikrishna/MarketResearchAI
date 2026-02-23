"""
Unified Dual-Mode Pipeline Orchestrator.
Exploratory: Stage 0E → Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 6 (Synthesis) → Report.
Problem-Driven: Stage 0P → Taxonomy → Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Stage 6 → Report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.agents.behavioral_ethologist import run as run_behavioral
from src.agents.competitive_strategist import run as run_competitive
from src.agents.decision_jury import run as run_jury
from src.agents.industry_scoper import run as run_industry_scoper
from src.agents.market_sizing_agent import run_exploratory as run_sizing_exploratory
from src.agents.market_sizing_agent import run_problem_driven as run_sizing_problem_driven
from src.agents.positioning_agent import run as run_positioning
from src.agents.problem_scoper import run as run_problem_scoper
from src.agents.segment_specialist import run as run_segment_specialist
from src.agents.taxonomy_architect import run as run_taxonomy
from src.models import (
    RESEARCH_MODE_EXPLORATORY,
    RESEARCH_MODE_PROBLEM_DRIVEN,
    Category,
    CategorySegments,
    CompetitionGaps,
    PainPoints,
    Section1,
    Stage0EOutput,
    Stage0POutput,
)


ProgressCallback = Callable[[str, float, int | None], None]

# Stage labels for UI (exploratory and problem-driven share most)
AGENT_LABELS = [
    "Stage 0E/0P (Scoping)",
    "Stage 1 (Market Sizing)",
    "Taxonomy / Categories",
    "Segment Specialist",
    "Behavioral Ethologist",
    "Competitive Strategist",
    "Stage 5 (Positioning)",
    "Stage 6 (Synthesis / Jury)",
]


def _default_progress(_msg: str, _p: float, _completed: int | None = None) -> None:
    pass


def _save_artifact(artifact: dict[str, Any], output_path: str | Path | None) -> None:
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)


def _build_section1_from_exploratory(
    stage0e: Stage0EOutput,
    stage1_matrix: list[Any],
) -> Section1:
    """Build section1 (categories) from Stage 0E + Stage 1 matrix for downstream pipeline."""
    size_by_name = {r.category_name: r for r in stage1_matrix} if stage1_matrix else {}
    categories = []
    for tc in stage0e.categories:
        row = size_by_name.get(tc.name)
        categories.append(
            Category(
                name=tc.name,
                description=tc.description or "",
                tam=(row.market_size if row else None) or (tc.size_range or ""),
                som=(row.largest_segment_size if row else None) or "",
                historical_cagr=(row.historical_cagr if row else None) or "",
                projected_cagr=(row.projected_cagr or (row.segment_cagr if row else None) if row else None) or "",
                trends=[tc.growth_signal] if tc.growth_signal else [],
            )
        )
    return Section1(
        industry=stage0e.industry,
        summary=stage0e.summary or stage0e.industry,
        categories=categories,
    )


def run_pipeline(
    industry: str,
    *,
    mode: str = RESEARCH_MODE_EXPLORATORY,
    progress: ProgressCallback | None = None,
    output_path: str | Path | None = None,
    max_categories: int | None = None,
    max_segments_per_category: int | None = None,
    use_deep_research: bool = False,
    # Exploratory-only
    industry_boundaries_hint: str = "",
    # Problem-driven-only
    problem_statement: str = "",
    target_user: str = "",
    target_segment: str = "",
    market_money: str = "",
    user_behavior: str = "",
    competition: str = "",
    ai_advantage: str = "",
    hypotheses: list[str] | None = None,
    # Convergence (exploratory → problem-driven after Stage 4; optional)
    converge_to_problem: bool = False,
    converge_problem_statement: str = "",
) -> dict[str, Any]:
    """
    Run the Unified Dual-Mode pipeline. Returns the Research Artifact (dict).
    mode: "exploratory" | "problem_driven"
    use_deep_research: If True, use Gemini Deep Research Agent for Stage 0E (and future stages) for web-backed insights.
    """
    report = _default_progress if progress is None else progress
    progress_dr = (lambda msg, p: report(msg, p, None)) if progress else None
    artifact: dict[str, Any] = {
        "mode": mode,
        "industry": industry,
        "stage0e": None,
        "stage0p": None,
        "stage1": None,
        "section1": None,
        "section2": [],
        "section3": [],
        "section4": [],
        "stage5": None,
        "jury": None,
        "convergence_choice": None,
    }

    if mode == RESEARCH_MODE_EXPLORATORY:
        # --- Stage 0E: Industry Scoper ---
        report("Stage 0E — Industry Scoping…" + (" (Deep Research, may take several minutes)" if use_deep_research else ""), 0.02, None)
        stage0e = run_industry_scoper(
            industry,
            industry_boundaries_hint=industry_boundaries_hint,
            use_deep_research=use_deep_research,
            progress_callback=progress_dr,
        )
        artifact["stage0e"] = stage0e.model_dump()
        artifact["industry"] = stage0e.industry
        report("Stage 0E — Completed", 0.08, 0)

        # --- Stage 1: Market Sizing (Exploratory) ---
        report("Stage 1 — Market Sizing (exploratory)…", 0.10, None)
        categories_for_sizing = [c.model_dump() for c in stage0e.categories]
        stage1 = run_sizing_exploratory(
            industry=stage0e.industry,
            context=stage0e.summary,
            categories=categories_for_sizing,
        )
        artifact["stage1"] = stage1.model_dump()
        report("Stage 1 — Completed", 0.18, 1)

        # Build section1 from 0E + stage1 for rest of pipeline
        section1 = _build_section1_from_exploratory(stage0e, stage1.category_sizing_matrix)
        artifact["section1"] = section1.model_dump()
        categories = section1.categories
        report("Categories (from taxonomy) ready.", 0.18, 2)
    else:
        # --- Stage 0P: Problem Scoper ---
        report("Stage 0P — Problem Scoping…", 0.02, None)
        stage0p = run_problem_scoper(
            industry=industry,
            problem_statement=problem_statement,
            target_user=target_user,
            target_segment=target_segment,
            market_money=market_money,
            user_behavior=user_behavior,
            competition=competition,
            ai_advantage=ai_advantage,
            hypotheses=hypotheses or [],
        )
        artifact["stage0p"] = stage0p.model_dump()
        report("Stage 0P — Completed", 0.08, 0)

        # --- Taxonomy (Section 1) ---
        report("Taxonomy Architect — Running…", 0.10, None)
        section1 = run_taxonomy(industry)
        artifact["section1"] = section1.model_dump()
        artifact["industry"] = section1.industry
        report("Taxonomy — Completed", 0.18, 2)

        # --- Stage 1: Market Sizing (Problem-Driven) ---
        report("Stage 1 — Market Sizing (problem-driven)…", 0.20, None)
        stage0p_obj = Stage0POutput(**artifact["stage0p"])
        stage1 = run_sizing_problem_driven(
            industry=industry,
            problem_summary=stage0p_obj.summary or stage0p_obj.problem_statement,
            target_user=stage0p_obj.target_user,
            target_segment=stage0p_obj.target_segment,
            categories=section1.model_dump().get("categories") or [],
        )
        artifact["stage1"] = stage1.model_dump()
        report("Stage 1 — Completed", 0.28, 1)
        categories = section1.categories
    # --- End of mode-specific start; from here both paths use section1 + categories ---

    if max_categories is not None:
        categories = categories[:max_categories]
    if not categories:
        report("No categories; running synthesis on partial artifact.", 0.90, None)
        artifact["jury"] = run_jury(artifact).model_dump()
        _save_artifact(artifact, output_path)
        report("Done.", 1.0, 7)
        return artifact

    # --- Stage 2: Segment Specialist (per category) ---
    section2_list: list[CategorySegments] = []
    total_cats = len(categories)
    summary = (artifact.get("section1") or {}).get("summary") or f"Industry: {artifact.get('industry')}"
    for i, cat in enumerate(categories):
        report(f"Segment Specialist — {cat.name} ({i + 1}/{total_cats})…", 0.28 + 0.12 * (i / max(1, total_cats)), None)
        cat_segments = run_segment_specialist(
            category_name=cat.name,
            industry_summary=summary,
            category_context=cat.description or "; ".join(cat.trends),
        )
        section2_list.append(cat_segments)
        artifact["section2"] = [s.model_dump() for s in section2_list]

    report("Segment Specialist — Completed", 0.45, 3)

    segment_tasks: list[tuple[str, str, str]] = []
    for cs in section2_list:
        segs = cs.segments
        if max_segments_per_category is not None:
            segs = segs[: max_segments_per_category]
        for seg in segs:
            segment_tasks.append((cs.category_name, seg.name, seg.description or seg.notes))

    if not segment_tasks:
        report("No segments; running synthesis.", 0.90, None)
        artifact["jury"] = run_jury(artifact).model_dump()
        _save_artifact(artifact, output_path)
        report("Done.", 1.0, 7)
        return artifact

    # --- Stage 3 (Pain) & Stage 4 (Competition) per segment ---
    total_tasks = len(segment_tasks)
    section3_list: list[PainPoints] = []
    for idx, (cat_name, seg_name, seg_ctx) in enumerate(segment_tasks):
        report(f"Behavioral Ethologist — {cat_name} / {seg_name}…", 0.45 + 0.20 * (idx / max(1, total_tasks)), None)
        pp = run_behavioral(category_name=cat_name, segment_name=seg_name, segment_context=seg_ctx)
        section3_list.append(pp)
        artifact["section3"] = [p.model_dump() for p in section3_list]

    report("Behavioral Ethologist — Completed", 0.68, 4)

    section4_list: list[CompetitionGaps] = []
    for idx, pp in enumerate(section3_list):
        report(f"Competitive Strategist — {pp.category_name} / {pp.segment_name}…", 0.68 + 0.12 * (idx / max(1, total_tasks)), None)
        cg = run_competitive(pain_points=pp)
        section4_list.append(cg)
        artifact["section4"] = [c.model_dump() for c in section4_list]

    report("Competitive Strategist — Completed", 0.82, 5)

    # --- Stage 5: Positioning (Problem-Driven only) ---
    if mode == RESEARCH_MODE_PROBLEM_DRIVEN:
        report("Stage 5 — Positioning…", 0.84, None)
        stage5 = run_positioning(artifact)
        artifact["stage5"] = stage5.model_dump()
        report("Stage 5 — Completed", 0.88, 6)

    # --- Stage 6: Synthesis / Decision Jury ---
    report("Stage 6 — Synthesis / Jury…", 0.88, None)
    jury_output = run_jury(artifact)
    artifact["jury"] = jury_output.model_dump()
    _save_artifact(artifact, output_path)
    report("Pipeline complete.", 1.0, 7)
    return artifact
