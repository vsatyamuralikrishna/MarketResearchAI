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


class TaxonomyQuantification(BaseModel):
    """Explicit counts and summary at end of Stage 0E."""

    categories_count: int = 0
    segments_count: int = 0
    size_orders_summary: str = ""  # e.g. "Category X: $10-50B; Category Y: $1-10B"
    growth_signals_summary: str = ""  # e.g. "3 growing, 2 emerging, 1 mature"


class Stage0EOutput(BaseModel):
    """Stage 0E deliverable: Industry Taxonomy Map."""

    industry: str = ""
    level1_industry_name: str = ""  # explicit Level 1 for taxonomy table
    industry_boundaries: str = ""
    value_chain_summary: str = ""
    industry_classification: str = ""  # NAICS, analyst classifications (Gartner/McKinsey, etc.)
    pestel_overview: str = ""  # half-page PESTEL: regulatory, economic, tech, sociocultural
    categories: list[TaxonomyCategory] = Field(default_factory=list)
    taxonomy_quantification: TaxonomyQuantification | None = None
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
    historical_cagr: str = ""
    projected_cagr: str = ""
    largest_segment_name: str = ""
    largest_segment_size: str = ""
    segment_cagr: str = ""
    key_segments: list[str] = Field(default_factory=list)  # segment names in this category
    growth_drivers: list[str] = Field(default_factory=list)  # 3-4 bullets per category
    headwinds: list[str] = Field(default_factory=list)  # 3-4 bullets per category
    growth_signal: str = ""  # emerging | growing | mature | declining


class TAMSAMSOM(BaseModel):
    """Problem-driven: TAM → SAM → SOM funnel."""

    tam: str = ""
    sam: str = ""
    som: str = ""
    assumptions: str = ""
    growth_forecast: str = ""


class Stage1Output(BaseModel):
    """Stage 1: Market Sizing deliverable."""

    mode: str = ""
    mode_clarification: str = ""  # e.g. "Stage 1 Exploratory: TAM per category/segment; SAM/SOM not modeled"
    category_sizing_matrix: list[CategorySizingRow] = Field(default_factory=list)
    tam_sam_som: TAMSAMSOM | None = None
    summary: str = ""


# --- Section 2: Segments (Agent 2) — Stage 2 Segment Deep-Dive ---


class SegmentPlayer(BaseModel):
    """Top player in segment with market share."""

    name: str = ""
    market_share: str = ""
    market_share_band: str = ""  # e.g. "top 3 control 60-70%"
    business_model: str = ""
    pricing_note: str = ""


class Segment(BaseModel):
    """Single segment within a category (Stage 2 extended)."""

    name: str
    segment_type: str = ""
    description: str = ""
    growth_drivers: list[str] = Field(default_factory=list)
    under_capitalized: bool = False
    over_saturated: bool = False
    notes: str = ""
    top_players: list[SegmentPlayer] = Field(default_factory=list)
    pricing_range: str = ""
    technology_stack: str = ""
    regulatory_requirements: str = ""
    funding_landscape: str = ""
    hhi_note: str = ""
    num_players_estimate: str = ""  # e.g. "15-20", "5-8"
    concentration_band: str = ""  # fragmented | moderate | concentrated
    segment_deep_dive_summary: str = ""  # one-line for matrix row


class SegmentDeepDiveRow(BaseModel):
    """One row in Stage 2 segment deep-dive matrix."""

    segment_name: str = ""
    category_name: str = ""
    size: str = ""
    cagr: str = ""
    num_players: str = ""
    concentration_hhi_band: str = ""
    business_model: str = ""
    pricing_band: str = ""


class CategorySegments(BaseModel):
    """Section 2 slice: segments for one category."""

    category_name: str
    segments: list[Segment] = Field(default_factory=list)


# --- Section 3: Pain Points (Agent 3) — Stage 4 Customer & Demand ---


class PersonaCard(BaseModel):
    """Persona per segment: demographics, JTBD, triggers, WTP, channels."""

    name: str = ""  # e.g. "College Student with Social Anxiety"
    demographics: str = ""
    jobs_to_be_done: list[str] = Field(default_factory=list)
    triggers: str = ""
    willingness_to_pay_range: str = ""
    preferred_channels: str = ""
    notes: str = ""


class PainPoints(BaseModel):
    """Section 3 slice: user pain points for one segment (Stage 4 extended)."""

    category_name: str = ""
    segment_name: str = ""
    zero_moment_of_truth: str = ""
    alternative_paths: list[str] = Field(default_factory=list)
    retention_killers: list[str] = Field(default_factory=list)
    notes: str = ""
    persona_summary: str = ""
    persona_cards: list[PersonaCard] = Field(default_factory=list)
    jobs_to_be_done: list[str] = Field(default_factory=list)
    demand_signals: str = ""
    willingness_to_pay: str = ""
    customer_journey_summary: str = ""  # trigger → search → trial → adoption → churn (textual)


# --- Section 4: Competition (Agent 4) — Stage 3 Competitive Landscape ---


class BattleCard(BaseModel):
    """Battle card: value prop, strengths, weaknesses, pricing, GTM, key features."""

    competitor_name: str = ""
    value_proposition: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    pricing: str = ""
    gtm_summary: str = ""
    key_features: list[str] = Field(default_factory=list)  # for feature matrix


class CompetitionGaps(BaseModel):
    """Section 4 slice: competition and gaps for one segment (Stage 3 extended)."""

    category_name: str = ""
    segment_name: str = ""
    delivery_mechanisms: list[str] = Field(default_factory=list)
    product_feature_gaps: list[str] = Field(default_factory=list)
    experience_gaps: list[str] = Field(default_factory=list)
    moat_assessment: str = ""
    notes: str = ""
    porter_five_forces_summary: str = ""
    porter_five_forces_detail: str = ""  # explicit 5 forces (threat of new entry, rivalry, etc.)
    competitive_matrix_note: str = ""
    feature_matrix_summary: str = ""  # grid of players × key features (text or structured)
    positioning_2x2_axes: str = ""  # e.g. "Degree of specialization (low→high) vs Digital tooling depth"
    positioning_2x2_note: str = ""  # where incumbents and wedge sit
    battle_cards: list[BattleCard] = Field(default_factory=list)


# --- Stage 5: Positioning & Competitive Edge (Problem-Driven only) ---


class SegmentPositioningBrief(BaseModel):
    """One-page problem & positioning brief per recommended segment."""

    segment_name: str = ""
    problem_statement: str = ""
    target_user: str = ""
    current_alternatives: str = ""
    why_now: str = ""
    proposed_offering: str = ""
    unique_edge: str = ""
    price_anchor: str = ""  # e.g. "$X/month D2C or $Y PMPM employer"


class Stage5Output(BaseModel):
    """Stage 5: GTM Strategy + Positioning."""

    unique_competitive_advantage: str = ""
    positioning_summary: str = ""
    positioning_statement: str = ""  # explicit one-liner
    perceptual_map_2x2_note: str = ""  # axes + where we sit vs incumbents
    pricing_strategy: str = ""
    price_anchor_per_segment: str = ""  # rough anchor for recommended segments
    funding_required: str = ""
    break_even_summary: str = ""
    gtm_strategy: str = ""
    recommended_investors: list[str] = Field(default_factory=list)
    segment_briefs: list[SegmentPositioningBrief] = Field(default_factory=list)


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


def _ensure_str_list(v: Any) -> list[str]:
    """Coerce to list of strings; LLM sometimes returns a single string for list fields."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        return [v] if v.strip() else []
    return []


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


class AttractivenessRow(BaseModel):
    """One row in segment attractiveness scoring table (Stage 6)."""

    segment_name: str = ""
    category_name: str = ""
    size_score: str = ""  # or 1-5
    growth_score: str = ""
    competition_intensity: str = ""
    accessibility: str = ""
    regulatory_risk: str = ""
    overall_score: str = ""


class ScenarioAnalysis(BaseModel):
    """Best / base / worst for top segment (Stage 6)."""

    segment_name: str = ""
    base_case: str = ""
    best_case: str = ""
    worst_case: str = ""
    assumptions_note: str = ""


class JuryOutput(BaseModel):
    """Decision Jury / Stage 6 Synthesis structured output."""

    conflict_check: str = ""
    moat_assessment: str = ""
    resource_allocation: str = ""
    segment_verdicts: list[SegmentVerdict] = Field(default_factory=list)
    executive_summary: str = ""
    synthesis_type: str = ""
    opportunity_heat_map_summary: str = ""
    segment_attractiveness_table: list[AttractivenessRow] = Field(default_factory=list)
    scenario_analysis: ScenarioAnalysis | None = None
    strategic_recommendations: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    slide_outline: list[dict[str, Any]] = Field(default_factory=list)  # [{slide_number, title, bullets}]

    @field_validator("conflict_check", "moat_assessment", "resource_allocation", "executive_summary", "synthesis_type", "opportunity_heat_map_summary", mode="before")
    @classmethod
    def _str_fields(cls, v: Any) -> str:
        return _coerce_str(v)


# --- Stage 7: Deliverables — McKinsey-style slide outline ---


class SlideOutlineItem(BaseModel):
    """One slide in the deck outline."""

    slide_number: int = 0
    title: str = ""
    bullets: list[str] = Field(default_factory=list)


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
        "slide_outline": [],
    }
