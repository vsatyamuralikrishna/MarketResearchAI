"""
Pydantic models for Research Artifact (Sections 1-4) and Decision Jury output.
Used by agents, orchestrator, and report builder.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Section 1: Taxonomy (Agent 1) ---


class Category(BaseModel):
    """Single category from Taxonomy Architect."""

    name: str
    description: str = ""
    tam: str = ""  # Total Addressable Market
    som: str = ""  # Serviceable Obtainable Market
    historical_cagr: str = ""
    projected_cagr: str = ""
    trends: list[str] = Field(default_factory=list)


class Section1(BaseModel):
    """Section 1: Categories, Market Cap, Trends."""

    industry: str = ""
    summary: str = ""
    categories: list[Category] = Field(default_factory=list)


# --- Section 2: Segments (Agent 2) ---


class Segment(BaseModel):
    """Single segment within a category."""

    name: str
    segment_type: str = ""  # primary | secondary
    description: str = ""
    growth_drivers: list[str] = Field(default_factory=list)
    under_capitalized: bool = False
    over_saturated: bool = False
    notes: str = ""


class CategorySegments(BaseModel):
    """Section 2 slice: segments for one category."""

    category_name: str
    segments: list[Segment] = Field(default_factory=list)


# --- Section 3: Pain Points (Agent 3) ---


class PainPoints(BaseModel):
    """Section 3 slice: user pain points for one segment."""

    category_name: str = ""
    segment_name: str = ""
    zero_moment_of_truth: str = ""
    alternative_paths: list[str] = Field(default_factory=list)
    retention_killers: list[str] = Field(default_factory=list)
    notes: str = ""


# --- Section 4: Competition (Agent 4) ---


class CompetitionGaps(BaseModel):
    """Section 4 slice: competition and gaps for one segment."""

    category_name: str = ""
    segment_name: str = ""
    delivery_mechanisms: list[str] = Field(default_factory=list)  # API, SaaS, etc.
    product_feature_gaps: list[str] = Field(default_factory=list)
    experience_gaps: list[str] = Field(default_factory=list)
    moat_assessment: str = ""
    notes: str = ""


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
    """Decision Jury structured output."""

    conflict_check: str = ""
    moat_assessment: str = ""
    resource_allocation: str = ""  # $1M recommendation
    segment_verdicts: list[SegmentVerdict] = Field(default_factory=list)
    executive_summary: str = ""

    @field_validator("conflict_check", "moat_assessment", "resource_allocation", "executive_summary", mode="before")
    @classmethod
    def _str_fields(cls, v: Any) -> str:
        return _coerce_str(v)


# --- Research Artifact (full state) ---


def research_artifact_schema() -> dict[str, Any]:
    """Return a JSON-serializable schema description for the full artifact."""
    return {
        "industry": "",
        "section1": {
            "industry": "",
            "summary": "",
            "categories": [],
        },
        "section2": [],  # list of CategorySegments
        "section3": [],  # list of PainPoints (keyed by category_name + segment_name)
        "section4": [],  # list of CompetitionGaps
        "jury": None,  # JuryOutput or None
    }
