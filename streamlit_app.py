"""
Streamlit UI: Industry input → Run pipeline with progress → View/Download report.
"""
import os
import sys
from pathlib import Path

# Add project root so "src" imports work (e.g. when running: streamlit run streamlit_app.py)
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

# Load .env for GEMINI_API_KEY when not in Streamlit secrets
try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except Exception:
    pass

from src.models import RESEARCH_MODE_EXPLORATORY, RESEARCH_MODE_PROBLEM_DRIVEN, _coerce_str
from src.orchestrator import AGENT_LABELS, run_pipeline
from src.report.builder import build_html, build_pdf


def _jury_str(jury: dict, key: str) -> str:
    """Get jury field as string; coerce dict/list from malformed or old artifacts."""
    return _coerce_str(jury.get(key))


st.set_page_config(page_title="Market Research AI", page_icon="📊", layout="wide")

# Brick Red, Blue & White theme — custom CSS
st.markdown("""
<style>
    /* Main title */
    h1 {
        color: #1E3A5F !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #B22222;
        padding-bottom: 0.3em;
    }
    /* Subtitle / body text */
    p, .stMarkdown {
        color: #1E3A5F !important;
    }
    /* Run Research button — single blue, white text, simple hover (shadow only) */
    .stButton > button,
    [data-testid="stButton"] button,
    section.main .stButton button,
    .stButton > button kbd,
    .stButton > button span {
        background-color: #1E3A5F !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        transition: box-shadow 0.2s ease;
    }
    .stButton > button:hover,
    [data-testid="stButton"] button:hover {
        background-color: #1E3A5F !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(30, 58, 95, 0.5);
    }
    /* Expander */
    .streamlit-expanderHeader {
        background: #F0F4F8 !important;
        color: #1E3A5F !important;
        border-left: 4px solid #B22222 !important;
    }
    /* Success message */
    .stSuccess {
        background: linear-gradient(90deg, #E8F0FE 0%, #F0F4F8 100%) !important;
        border-left: 4px solid #2563EB !important;
        color: #1E3A5F !important;
    }
    /* Report tabs — Brick red background, white text */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #B22222 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        border-radius: 8px 8px 0 0;
        border: 1px solid #8B0000;
    }
    .stTabs [data-baseweb="tab"] *,
    .stTabs [data-baseweb="tab"] span {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    .stTabs [aria-selected="true"] {
        background: #8B0000 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] span {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #B22222, #2563EB) !important;
    }
    /* Input field focus */
    .stTextInput input:focus {
        box-shadow: 0 0 0 2px #B22222 !important;
        border-color: #B22222 !important;
    }
    /* Download buttons */
    a[download] {
        background: #2563EB !important;
        color: white !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
    }
    /* Pipeline progress box */
    div[data-testid="stMarkdownContainer"] p {
        color: #1E3A5F !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Market Research AI")
st.markdown("**Unified Dual-Mode Framework:** Exploratory (industry landscape) or Problem-Driven (validate an idea).")

industry = st.text_input(
    "Industry / Area",
    placeholder="e.g. FinTech, Healthcare IT, EdTech, Mental Health",
    key="industry",
)

mode = st.radio(
    "Research mode",
    options=[RESEARCH_MODE_EXPLORATORY, RESEARCH_MODE_PROBLEM_DRIVEN],
    format_func=lambda x: "Exploratory — understand this industry" if x == RESEARCH_MODE_EXPLORATORY else "Problem-Driven — validate a problem/idea",
    key="mode",
    horizontal=True,
)

# Mode-specific inputs
if mode == RESEARCH_MODE_EXPLORATORY:
    industry_boundaries_hint = st.text_area(
        "Industry boundaries / analyst sources (optional)",
        placeholder="e.g. Broad definition, adjacent industries (wellness, pharma), NAICS or analyst segments to align with",
        key="industry_boundaries",
        height=80,
    )
    problem_statement = target_user = target_segment = ""
    market_money = user_behavior = competition = ai_advantage = ""
    hypotheses_list = []
else:
    industry_boundaries_hint = ""
    st.markdown("**Problem scoping (Stage 0P)**")
    problem_statement = st.text_area(
        "Problem statement",
        placeholder="e.g. Can an AI therapy chatbot compete with BetterHelp? Who is the user and what pain do they have?",
        key="problem_statement",
        height=100,
    )
    target_user = st.text_input("Target user", placeholder="e.g. Adults 25–45 seeking affordable therapy", key="target_user")
    target_segment = st.text_input("Target segment", placeholder="e.g. Employer-sponsored digital mental health", key="target_segment")
    with st.expander("Validation questions (optional)"):
        market_money = st.text_area("Market Money: Where is money spent? Who is incentivized?", placeholder="Budget line, who pays", key="market_money", height=60)
        user_behavior = st.text_area("User Behavior: When does pain occur? What do users try first?", key="user_behavior", height=60)
        competition = st.text_area("Competition: Good-enough incumbents? Why do people still complain?", key="competition", height=60)
        ai_advantage = st.text_area("AI Advantage: What is expensive/slow/inconsistent? Repetitive high-impact decisions?", key="ai_advantage", height=60)
    hypotheses_text = st.text_area(
        "Hypotheses to validate (one per line)",
        placeholder="Hypothesis 1\nHypothesis 2",
        key="hypotheses",
        height=80,
    )
    hypotheses_list = [h.strip() for h in (hypotheses_text or "").split("\n") if h.strip()]

# Optional limits for demo
with st.expander("Options (limits for faster demo)"):
    max_categories = st.number_input("Max categories (0 = no limit)", min_value=0, value=0, step=1)
    max_segments = st.number_input("Max segments per category (0 = no limit)", min_value=0, value=0, step=1)
    max_cat = None if max_categories == 0 else max_categories
    max_seg = None if max_segments == 0 else max_segments

run_clicked = st.button("Run Research")

# Reinject button style after button so it wins over Streamlit theme
st.markdown("""
<style>
.stButton > button { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
.stButton > button * { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
.stButton > button:hover { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
.stButton > button:hover * { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

if run_clicked and not industry.strip():
    st.warning("Please enter an industry or area.")
    run_clicked = False
if run_clicked and mode == RESEARCH_MODE_PROBLEM_DRIVEN and not (problem_statement or "").strip():
    st.warning("Problem-Driven mode requires a problem statement.")
    run_clicked = False

if run_clicked and industry.strip():
    progress_placeholder = st.empty()
    bar = st.progress(0.0)
    status = st.empty()
    if "_completed_agents" not in st.session_state:
        st.session_state["_completed_agents"] = set()
    st.session_state["_completed_agents"].clear()

    def report_progress(msg: str, p: float, completed_agent: int | None = None) -> None:
        if completed_agent is not None:
            st.session_state["_completed_agents"].add(completed_agent)
        bar.progress(min(1.0, max(0.0, p)))
        completed = st.session_state["_completed_agents"]
        lines = [f"- {'✅' if i in completed else '⏳'} {label}" for i, label in enumerate(AGENT_LABELS)]
        status.markdown("\n".join([
            "**Pipeline progress**",
            "",
            "\n".join(lines),
            "",
            f"**Current:** {msg}",
        ]))

    kwargs = dict(
        industry=industry.strip(),
        mode=mode,
        progress=report_progress,
        output_path=_project_root / "output" / "artifact.json",
        max_categories=max_cat,
        max_segments_per_category=max_seg,
    )
    if mode == RESEARCH_MODE_EXPLORATORY:
        kwargs["industry_boundaries_hint"] = (industry_boundaries_hint or "").strip()
    else:
        kwargs["problem_statement"] = (problem_statement or "").strip()
        kwargs["target_user"] = (target_user or "").strip()
        kwargs["target_segment"] = (target_segment or "").strip()
        kwargs["market_money"] = (market_money or "").strip()
        kwargs["user_behavior"] = (user_behavior or "").strip()
        kwargs["competition"] = (competition or "").strip()
        kwargs["ai_advantage"] = (ai_advantage or "").strip()
        kwargs["hypotheses"] = hypotheses_list

    try:
        artifact = run_pipeline(**kwargs)
    except Exception as e:
        progress_placeholder.empty()
        bar.empty()
        status.empty()
        st.error(f"Pipeline failed: {e}")
        raise

    progress_placeholder.empty()
    bar.empty()
    status.empty()
    st.success("Report ready.")

    # Persist artifact in session for report view/download
    st.session_state["artifact"] = artifact

# If we have an artifact (from this run or reload), show report
artifact = st.session_state.get("artifact")
if artifact:
    st.divider()
    st.subheader("Report")

    tab_names = [
        "Executive Summary",
        "Scoping (0E/0P)",
        "Market Sizing (Stage 1)",
        "Categories & Segments",
        "Pain Points & Demand",
        "Competition & Gaps",
        "Positioning (Stage 5)",
        "Synthesis & Jury",
        "Download",
    ]
    tabs = st.tabs(tab_names)

    s1 = artifact.get("section1") or {}
    jury = artifact.get("jury") or {}
    section2 = artifact.get("section2") or []
    section3 = artifact.get("section3") or []
    section4 = artifact.get("section4") or []
    stage0e = artifact.get("stage0e") or {}
    stage0p = artifact.get("stage0p") or {}
    stage1 = artifact.get("stage1") or {}
    stage5 = artifact.get("stage5") or {}
    art_mode = artifact.get("mode") or "exploratory"

    with tabs[0]:
        st.markdown(_jury_str(jury, "executive_summary") or s1.get("summary") or stage0e.get("summary") or stage0p.get("summary") or "No summary.")

    with tabs[1]:
        if art_mode == RESEARCH_MODE_EXPLORATORY and stage0e:
            st.markdown("**Stage 0E: Industry Taxonomy**")
            st.markdown(stage0e.get("industry_boundaries") or "—")
            st.markdown("**Value chain:** " + (stage0e.get("value_chain_summary") or "—"))
            for cat in stage0e.get("categories") or []:
                st.markdown(f"- **{cat.get('name')}** ({cat.get('size_range')}, {cat.get('growth_signal')})")
                for sc in cat.get("subcategories") or []:
                    for seg in sc.get("segments") or []:
                        st.caption(f"  → {sc.get('name')} / {seg.get('name')}")
        elif stage0p:
            st.markdown("**Stage 0P: Problem Statement Brief**")
            st.markdown(stage0p.get("problem_statement") or "—")
            st.markdown("**Target user:** " + (stage0p.get("target_user") or "—"))
            st.markdown("**Target segment:** " + (stage0p.get("target_segment") or "—"))
            for k in ("market_money", "user_behavior", "competition", "ai_advantage"):
                if stage0p.get(k):
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {stage0p.get(k)}")
            for h in stage0p.get("hypotheses") or []:
                st.markdown(f"- {h}")
        else:
            st.info("No scoping data for this run.")

    with tabs[2]:
        st.markdown("**Stage 1: Market Sizing**")
        if stage1.get("category_sizing_matrix"):
            for row in stage1.get("category_sizing_matrix") or []:
                st.markdown(f"- **{row.get('category_name')}**: {row.get('market_size')} | CAGR {row.get('cagr')} | Largest: {row.get('largest_segment_name')} ({row.get('largest_segment_size')})")
        if stage1.get("tam_sam_som"):
            tss = stage1["tam_sam_som"]
            st.markdown("**TAM:** " + (tss.get("tam") or "—"))
            st.markdown("**SAM:** " + (tss.get("sam") or "—"))
            st.markdown("**SOM:** " + (tss.get("som") or "—"))
            st.markdown("**Assumptions:** " + (tss.get("assumptions") or "—"))
        st.caption(stage1.get("summary") or "")

    with tabs[3]:
        st.markdown("**Categories, Market Cap & Trends**")
        for c in s1.get("categories") or []:
            st.markdown(f"- **{c.get('name')}**: TAM {c.get('tam')} / SOM {c.get('som')} | CAGR {c.get('historical_cagr')} → {c.get('projected_cagr')}")
            st.caption("; ".join(c.get("trends") or []))
        st.markdown("**Segmented Decomposition**")
        for cs in section2:
            st.markdown(f"**{cs.get('category_name')}**")
            for seg in cs.get("segments") or []:
                st.markdown(f"- {seg.get('name')} ({seg.get('segment_type')}): {seg.get('description')}")
                st.caption("Drivers: " + "; ".join(seg.get("growth_drivers") or []))
                if seg.get("top_players"):
                    st.caption("Players: " + ", ".join(f"{p.get('name')} ({p.get('market_share')})" for p in seg.get("top_players") or []))

    with tabs[4]:
        st.markdown("**User Pain Points & Demand**")
        for pp in section3:
            st.markdown(f"**{pp.get('category_name')} / {pp.get('segment_name')}**")
            st.markdown(f"- ZMOT: {pp.get('zero_moment_of_truth')}")
            st.markdown(f"- Alternatives: {'; '.join(pp.get('alternative_paths') or [])}")
            st.markdown(f"- Retention killers: {'; '.join(pp.get('retention_killers') or [])}")
            if pp.get("persona_summary"):
                st.markdown("**Persona:** " + pp.get("persona_summary"))
            if pp.get("jobs_to_be_done"):
                st.markdown("**JTBD:** " + "; ".join(pp.get("jobs_to_be_done") or []))
            if pp.get("willingness_to_pay"):
                st.markdown("**WTP:** " + pp.get("willingness_to_pay"))

    with tabs[5]:
        st.markdown("**Competition, Delivery & Gaps**")
        for cg in section4:
            st.markdown(f"**{cg.get('category_name')} / {cg.get('segment_name')}**")
            st.markdown(f"- Delivery: {', '.join(cg.get('delivery_mechanisms') or [])}")
            st.markdown(f"- Product gaps: {'; '.join(cg.get('product_feature_gaps') or [])}")
            st.markdown(f"- Moat: {cg.get('moat_assessment')}")
            if cg.get("porter_five_forces_summary"):
                st.markdown("**Porter's Five Forces:** " + cg.get("porter_five_forces_summary"))
            for bc in cg.get("battle_cards") or []:
                st.markdown(f"  **Battle card — {bc.get('competitor_name')}:** {bc.get('value_proposition')}")

    with tabs[6]:
        if art_mode == RESEARCH_MODE_PROBLEM_DRIVEN and stage5:
            st.markdown("**Stage 5: Positioning & GTM**")
            st.markdown("**Competitive advantage:** " + (stage5.get("unique_competitive_advantage") or "—"))
            st.markdown("**Positioning:** " + (stage5.get("positioning_summary") or "—"))
            st.markdown("**Pricing:** " + (stage5.get("pricing_strategy") or "—"))
            st.markdown("**Funding:** " + (stage5.get("funding_required") or "—"))
            st.markdown("**Break-even:** " + (stage5.get("break_even_summary") or "—"))
            st.markdown("**GTM:** " + (stage5.get("gtm_strategy") or "—"))
            for inv in stage5.get("recommended_investors") or []:
                st.markdown(f"- {inv}")
        else:
            st.info("Positioning (Stage 5) runs only in Problem-Driven mode.")

    with tabs[7]:
        st.markdown("**Conflict Check**")
        st.markdown(_jury_str(jury, "conflict_check") or "—")
        st.markdown("**Moat Assessment**")
        st.markdown(_jury_str(jury, "moat_assessment") or "—")
        st.markdown("**Resource Allocation ($1M)**")
        st.markdown(_jury_str(jury, "resource_allocation") or "—")
        st.markdown("**Segment Verdicts**")
        for v in jury.get("segment_verdicts") or []:
            if not isinstance(v, dict):
                continue
            st.markdown(f"- {_coerce_str(v.get('category_name'))} / {_coerce_str(v.get('segment_name'))}: **{_coerce_str(v.get('verdict'))}** — {_coerce_str(v.get('rationale'))}")
        if jury.get("opportunity_heat_map_summary"):
            st.markdown("**Opportunity heat map:** " + _jury_str(jury, "opportunity_heat_map_summary"))
        for rec in jury.get("strategic_recommendations") or []:
            st.markdown(f"- {rec}")
        st.markdown("**Next steps**")
        for step in jury.get("next_steps") or []:
            st.markdown(f"- {step}")

    with tabs[8]:
        pdf_bytes = build_pdf(artifact)
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"market_research_{artifact.get('industry', 'report').replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
        html_content = build_html(artifact)
        st.download_button(
            "Download HTML",
            data=html_content,
            file_name=f"market_research_{artifact.get('industry', 'report').replace(' ', '_')}.html",
            mime="text/html",
        )
        st.markdown("---")
        st.markdown("Preview (HTML):")
        st.components.v1.html(html_content, height=600, scrolling=True)
