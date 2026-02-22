"""
Pydantic models for Unified Dual-Mode Research Framework.
Supports Exploratory and Problem-Driven modes; Stages 0E/0P through 7.
Backward compatible: section1-4 and jury remain for existing report builder.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Research mode and run config ---

RESEARCH_MODE_EXPLORATORY = "exploratory"
RESEARCH_MODE_PROBLEM_DRIVEN = "problem_driven"


# --- Stage 0E: Industry Scoping & Category Taxonomy (Exploratory) ---


class TaxonomySegment(BaseModel):
    """Level 4: Segment within a subcategory (4-level hierarchy)."""

    name: str
    description: str = ""
    key_players_initial: list[str] = Field(default_factory=list)
    size_range: str = ""  # e.g. <$1B, $1-10B
    growth_signal: str = ""  # emerging | growing | mature | declining


class TaxonomySubcategory(BaseModel):
    """Level 3: Subcategory within a category."""

    name: str
    description: str = ""
    segments: list[TaxonomySegment] = Field(default_factory=list)


class TaxonomyCategory(BaseModel):
    """Level 2: Category within industry (Stage 0E taxonomy)."""

    name: str
    description: str = ""
    subcategories: list[TaxonomySubcategory] = Field(default_factory=list)
    size_range: str = ""
    growth_signal: str = ""


class Stage0EOutput(BaseModel):
    """Stage 0E deliverable: Industry Taxonomy Map."""

    industry: str = ""
    industry_boundaries: str = ""
    value_chain_summary: str = ""
    categories: list[TaxonomyCategory] = Field(default_factory=list)
    summary: str = ""


# --- Stage 0P: Problem Scoping (Problem-Driven) ---


class Stage0POutput(BaseModel):
    """Stage 0P deliverable: Problem Statement Brief."""

    problem_statement: str = ""
    target_user: str = ""
    target_segment: str = ""
    market_money: str = ""
    user_behavior: str = ""
    competition: str = ""
    ai_advantage: str = ""
    hypotheses: list[str] = Field(default_factory=list)
    summary: str = ""


# --- Section 1: Taxonomy (Agent 1) — kept for compatibility; used in Problem-Driven or post-0E ---


class Category(BaseModel):
    """Single category from Taxonomy Architect."""

    name: str
    description: str = ""
    tam: str = ""  # Total Addressable Market
    som: str = ""  # Serviceable Obtainable Market
    sam: str = ""  # Serviceable Addressable Market (for TAM-SAM-SOM funnel)
    historical_cagr: str = ""
    projected_cagr: str = ""
    trends: list[str] = Field(default_factory=list)


class Section1(BaseModel):
    """Section 1: Categories, Market Cap, Trends."""

    industry: str = ""
    summary: str = ""
    categories: list[Category] = Field(default_factory=list)


# --- Stage 1: Market Sizing (both modes) ---


class CategorySizingRow(BaseModel):
    """One row in exploratory Category × Segment sizing matrix."""

    category_name: str = ""
    market_size: str = ""
    cagr: str = ""
    largest_segment_name: str = ""
    largest_segment_size: str = ""
    segment_cagr: str = ""


class TAMSAMSOM(BaseModel):
    """Problem-driven: TAM → SAM → SOM funnel."""

    tam: str = ""
    sam: str = ""
    som: str = ""
    assumptions: str = ""
    growth_forecast: str = ""


class Stage1Output(BaseModel):
    """Stage 1: Market Sizing deliverable."""

    mode: str = ""  # exploratory | problem_driven
    category_sizing_matrix: list[CategorySizingRow] = Field(default_factory=list)
    tam_sam_som: TAMSAMSOM | None = None
    summary: str = ""


# --- Section 2: Segments (Agent 2) — Stage 2 Segment Deep-Dive ---


class SegmentPlayer(BaseModel):
    """Top player in segment with market share."""

    name: str = ""
    market_share: str = ""
    business_model: str = ""


class Segment(BaseModel):
    """Single segment within a category (Stage 2 extended)."""

    name: str
    segment_type: str = ""  # primary | secondary
    description: str = ""
    growth_drivers: list[str] = Field(default_factory=list)
    under_capitalized: bool = False
    over_saturated: bool = False
    notes: str = ""
    # Stage 2 deep-dive
    top_players: list[SegmentPlayer] = Field(default_factory=list)
    pricing_range: str = ""
    technology_stack: str = ""
    regulatory_requirements: str = ""
    funding_landscape: str = ""
    hhi_note: str = ""  # concentration note


class CategorySegments(BaseModel):
    """Section 2 slice: segments for one category."""

    category_name: str
    segments: list[Segment] = Field(default_factory=list)


# --- Section 3: Pain Points (Agent 3) — Stage 4 Customer & Demand ---


class PainPoints(BaseModel):
    """Section 3 slice: user pain points for one segment (Stage 4 extended)."""

    category_name: str = ""
    segment_name: str = ""
    zero_moment_of_truth: str = ""
    alternative_paths: list[str] = Field(default_factory=list)
    retention_killers: list[str] = Field(default_factory=list)
    notes: str = ""
    # Stage 4 customer & demand
    persona_summary: str = ""
    jobs_to_be_done: list[str] = Field(default_factory=list)
    demand_signals: str = ""
    willingness_to_pay: str = ""


# --- Section 4: Competition (Agent 4) — Stage 3 Competitive Landscape ---


class BattleCard(BaseModel):
    """Problem-driven: battle card for one competitor."""

    competitor_name: str = ""
    value_proposition: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    gtm_summary: str = ""


class CompetitionGaps(BaseModel):
    """Section 4 slice: competition and gaps for one segment (Stage 3 extended)."""

    category_name: str = ""
    segment_name: str = ""
    delivery_mechanisms: list[str] = Field(default_factory=list)
    product_feature_gaps: list[str] = Field(default_factory=list)
    experience_gaps: list[str] = Field(default_factory=list)
    moat_assessment: str = ""
    notes: str = ""
    # Stage 3 competitive landscape
    porter_five_forces_summary: str = ""
    competitive_matrix_note: str = ""
    battle_cards: list[BattleCard] = Field(default_factory=list)


# --- Stage 5: Positioning & Competitive Edge (Problem-Driven only) ---


class Stage5Output(BaseModel):
    """Stage 5: GTM Strategy + Positioning."""

    unique_competitive_advantage: str = ""
    positioning_summary: str = ""
    pricing_strategy: str = ""
    funding_required: str = ""
    break_even_summary: str = ""
    gtm_strategy: str = ""
    recommended_investors: list[str] = Field(default_factory=list)


# --- Decision Jury (Agent 5) ---


def _coerce_str(v: Any) -> str:
    """Coerce to str for Jury/verdict fields; LLM sometimes returns dict/list."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return " | ".join(f"{k}: {_coerce_str(x)}" for k, x in v.items())
    if isinstance(v, list):
        return "; ".join(_coerce_str(x) for x in v)
    return str(v)


class SegmentVerdict(BaseModel):
    """Verdict for one segment (green/amber/red)."""

    category_name: str = ""
    segment_name: str = ""
    verdict: str = ""  # green | amber | red
    rationale: str = ""

    @field_validator("category_name", "segment_name", "verdict", "rationale", mode="before")
    @classmethod
    def _str_fields(cls, v: Any) -> str:
        return _coerce_str(v)


class JuryOutput(BaseModel):
    """Decision Jury / Stage 6 Synthesis structured output."""

    conflict_check: str = ""
    moat_assessment: str = ""
    resource_allocation: str = ""
    segment_verdicts: list[SegmentVerdict] = Field(default_factory=list)
    executive_summary: str = ""
    synthesis_type: str = ""
    opportunity_heat_map_summary: str = ""
    strategic_recommendations: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)

    @field_validator("conflict_check", "moat_assessment", "resource_allocation", "executive_summary", "synthesis_type", "opportunity_heat_map_summary", mode="before")
    @classmethod
    def _str_fields(cls, v: Any) -> str:
        return _coerce_str(v)


# --- Research Artifact (full state) ---


def research_artifact_schema() -> dict[str, Any]:
    """Return a JSON-serializable schema description for the full artifact."""
    return {
        "mode": "exploratory",
        "industry": "",
        "stage0e": None,
        "stage0p": None,
        "stage1": None,
        "section1": {"industry": "", "summary": "", "categories": []},
        "section2": [],
        "section3": [],
        "section4": [],
        "stage5": None,
        "jury": None,
        "convergence_choice": None,
    }
