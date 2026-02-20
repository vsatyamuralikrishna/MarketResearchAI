"""
Sequential Pipeline Orchestrator.
Runs Agent 1 → Agent 2 (per category) → Agent 3 (per segment) → Agent 4 (per segment) → Agent 5.
Merges results into a single Research Artifact and optionally persists to JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.agents.behavioral_ethologist import run as run_behavioral
from src.agents.competitive_strategist import run as run_competitive
from src.agents.decision_jury import run as run_jury
from src.agents.segment_specialist import run as run_segment_specialist
from src.agents.taxonomy_architect import run as run_taxonomy
from src.models import (
    CategorySegments,
    CompetitionGaps,
    PainPoints,
    Section1,
)


# (message, progress 0.0-1.0, completed_agent 1-5 or None)
ProgressCallback = Callable[[str, float, int | None], None]

AGENT_LABELS = [
    "Taxonomy Architect",
    "Segment Specialist",
    "Behavioral Ethologist",
    "Competitive Strategist",
    "Decision Jury",
]


def _default_progress(_msg: str, _p: float, _completed: int | None = None) -> None:
    pass


def run_pipeline(
    industry: str,
    *,
    progress: ProgressCallback | None = None,
    output_path: str | Path | None = None,
    max_concurrent: int = 2,
    max_categories: int | None = None,
    max_segments_per_category: int | None = None,
) -> dict[str, Any]:
    """
    Run the full 5-agent pipeline and return the Research Artifact (dict).
    Optionally persist to output_path (JSON).
    progress(message, 0.0..1.0) is called for UI updates.
    """
    report = _default_progress if progress is None else progress

    artifact: dict[str, Any] = {
        "industry": industry,
        "section1": None,
        "section2": [],
        "section3": [],
        "section4": [],
        "jury": None,
    }

    # --- Step 1: Taxonomy Architect ---
    report(f"{AGENT_LABELS[0]} — Running…", 0.05, None)
    section1 = run_taxonomy(industry)
    artifact["section1"] = section1.model_dump()
    artifact["industry"] = section1.industry
    summary = section1.summary or f"Industry: {section1.industry}; {len(section1.categories)} categories."
    report(f"{AGENT_LABELS[0]} — Completed", 0.15, 1)

    categories = section1.categories
    if max_categories is not None:
        categories = categories[: max_categories]

    if not categories:
        report("No categories; stopping.", 1.0, None)
        _save_artifact(artifact, output_path)
        return artifact

    # --- Step 2: Segment Specialist (per category) ---
    section2_list: list[CategorySegments] = []
    total_cats = len(categories)
    for i, cat in enumerate(categories):
        report(f"{AGENT_LABELS[1]} — Running: {cat.name} ({i + 1}/{total_cats})…", 0.15 + 0.15 * (i / max(1, total_cats)), None)
        cat_segments = run_segment_specialist(
            category_name=cat.name,
            industry_summary=summary,
            category_context=cat.description or "; ".join(cat.trends),
        )
        section2_list.append(cat_segments)
        artifact["section2"] = [s.model_dump() for s in section2_list]

    report(f"{AGENT_LABELS[1]} — Completed", 0.35, 2)

    # Flatten (category_name, segment) for steps 3 and 4
    segment_tasks: list[tuple[str, str, str]] = []  # (category_name, segment_name, segment_context)
    for cs in section2_list:
        segs = cs.segments
        if max_segments_per_category is not None:
            segs = segs[: max_segments_per_category]
        for seg in segs:
            segment_tasks.append((cs.category_name, seg.name, seg.description or seg.notes))

    if not segment_tasks:
        report("No segments; running Decision Jury on partial artifact.", 0.9, None)
        artifact["jury"] = run_jury(artifact).model_dump()
        _save_artifact(artifact, output_path)
        report("Done.", 1.0, 5)
        return artifact

    # --- Step 3: Behavioral Ethologist (per segment) ---
    section3_list: list[PainPoints] = []
    total_tasks = len(segment_tasks)
    for idx, (cat_name, seg_name, seg_ctx) in enumerate(segment_tasks):
        report(f"{AGENT_LABELS[2]} — Running: {cat_name} / {seg_name}…", 0.35 + 0.25 * (idx / max(1, total_tasks)), None)
        pp = run_behavioral(category_name=cat_name, segment_name=seg_name, segment_context=seg_ctx)
        section3_list.append(pp)
        artifact["section3"] = [p.model_dump() for p in section3_list]

    report(f"{AGENT_LABELS[2]} — Completed", 0.6, 3)

    # --- Step 4: Competitive Strategist (per segment, with its pain points) ---
    section4_list: list[CompetitionGaps] = []
    for idx, pp in enumerate(section3_list):
        report(f"{AGENT_LABELS[3]} — Running: {pp.category_name} / {pp.segment_name}…", 0.6 + 0.2 * (idx / max(1, total_tasks)), None)
        cg = run_competitive(pain_points=pp)
        section4_list.append(cg)
        artifact["section4"] = [c.model_dump() for c in section4_list]

    report(f"{AGENT_LABELS[3]} — Completed", 0.85, 4)

    # --- Step 5: Decision Jury ---
    report(f"{AGENT_LABELS[4]} — Running…", 0.88, None)
    jury_output = run_jury(artifact)
    artifact["jury"] = jury_output.model_dump()
    _save_artifact(artifact, output_path)
    report("Pipeline complete.", 1.0, 5)
    return artifact


def _save_artifact(artifact: dict[str, Any], output_path: str | Path | None) -> None:
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)
