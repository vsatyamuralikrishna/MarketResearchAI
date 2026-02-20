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

from src.models import _coerce_str
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
st.markdown("Multi-agent pipeline: Taxonomy → Segments → Pain Points → Competition → Decision Jury.")

industry = st.text_input(
    "Industry / Area",
    placeholder="e.g. FinTech, Healthcare IT, EdTech",
    key="industry",
)

# Optional limits for demo
with st.expander("Options (limits for faster demo)"):
    max_categories = st.number_input("Max categories (empty = no limit)", min_value=0, value=0, step=1)
    max_segments = st.number_input("Max segments per category (empty = no limit)", min_value=0, value=0, step=1)
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
        # Agent checklist: ✅ completed, ⏳ pending (one per line)
        lines = [f"- {'✅' if i in completed else '⏳'} {label}" for i, label in enumerate(AGENT_LABELS, 1)]
        status.markdown("\n".join([
            "**Pipeline progress**",
            "",
            "\n".join(lines),
            "",
            f"**Current:** {msg}",
        ]))

    try:
        artifact = run_pipeline(
            industry.strip(),
            progress=report_progress,
            output_path=_project_root / "output" / "artifact.json",
            max_categories=max_cat,
            max_segments_per_category=max_seg,
        )
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
        "Categories, Market Cap & Trends",
        "Segmented Decomposition",
        "User Pain Points & Friction",
        "Competition, Delivery & Gaps",
        "Decision Jury",
        "Download",
    ]
    tabs = st.tabs(tab_names)

    s1 = artifact.get("section1") or {}
    jury = artifact.get("jury") or {}
    section2 = artifact.get("section2") or []
    section3 = artifact.get("section3") or []
    section4 = artifact.get("section4") or []

    with tabs[0]:
        st.markdown(_jury_str(jury, "executive_summary") or s1.get("summary") or "No summary.")

    with tabs[1]:
        st.markdown("**Categories, Market Cap & Trends**")
        for c in s1.get("categories") or []:
            st.markdown(f"- **{c.get('name')}**: TAM {c.get('tam')} / SOM {c.get('som')} | CAGR {c.get('historical_cagr')} → {c.get('projected_cagr')}")
            st.caption("; ".join(c.get("trends") or []))

    with tabs[2]:
        st.markdown("**Segmented Decomposition**")
        for cs in section2:
            st.markdown(f"**{cs.get('category_name')}**")
            for seg in cs.get("segments") or []:
                st.markdown(f"- {seg.get('name')} ({seg.get('segment_type')}): {seg.get('description')}")
                st.caption("Drivers: " + "; ".join(seg.get("growth_drivers") or []))

    with tabs[3]:
        st.markdown("**User Pain Points & Friction**")
        for pp in section3:
            st.markdown(f"**{pp.get('category_name')} / {pp.get('segment_name')}**")
            st.markdown(f"- ZMOT: {pp.get('zero_moment_of_truth')}")
            st.markdown(f"- Alternatives: {'; '.join(pp.get('alternative_paths') or [])}")
            st.markdown(f"- Retention killers: {'; '.join(pp.get('retention_killers') or [])}")

    with tabs[4]:
        st.markdown("**Competition, Delivery & Gaps**")
        for cg in section4:
            st.markdown(f"**{cg.get('category_name')} / {cg.get('segment_name')}**")
            st.markdown(f"- Delivery: {', '.join(cg.get('delivery_mechanisms') or [])}")
            st.markdown(f"- Product gaps: {'; '.join(cg.get('product_feature_gaps') or [])}")
            st.markdown(f"- Moat: {cg.get('moat_assessment')}")

    with tabs[5]:
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

    with tabs[6]:
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
