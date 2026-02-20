"""
Report Builder: turns consolidated artifact + jury into multi-page PDF and HTML.
Industry-standard structure: title, methodology, executive summary, sections 1–5, optional appendix.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _esc(s: str) -> str:
    """Escape for use inside ReportLab Paragraphs."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _jury_str(jury: dict[str, Any], key: str) -> str:
    """Get jury field as string; coerce dict/list from older or malformed artifacts."""
    v = jury.get(key)
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return " | ".join(f"{k}: {x}" for k, x in v.items())
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return str(v)


def _to_str_val(v: Any) -> str:
    """Coerce any value to str (for verdict dict fields)."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return " | ".join(f"{k}: {_to_str_val(x)}" for k, x in v.items())
    if isinstance(v, list):
        return "; ".join(_to_str_val(x) for x in v)
    return str(v)


def build_pdf(artifact: dict[str, Any]) -> bytes:
    """Build a multi-page PDF from the research artifact. Returns PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=1 * inch,
        leftMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=6,
        spaceBefore=0,
    )
    h2_style = ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#1a1a1a"),
    )
    h3_style = ParagraphStyle(
        name="SubHeading",
        parent=styles["Heading3"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#333333"),
    )
    body = ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
        leading=13,
    )
    # Table cell style: smaller font, word wrap via Paragraph
    cell_style = ParagraphStyle(
        name="TableCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        spaceAfter=0,
        spaceBefore=0,
    )
    cell_header_style = ParagraphStyle(
        name="TableHeader",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        spaceAfter=0,
        spaceBefore=0,
        fontName="Helvetica-Bold",
        textColor=colors.whitesmoke,
    )

    story = []
    s1 = artifact.get("section1") or {}
    jury = artifact.get("jury") or {}
    industry = artifact.get("industry") or "Market Research"
    categories = s1.get("categories") or []

    # Title and date
    story.append(Paragraph(f"Market Research Report: {_esc(industry)}", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body))
    story.append(Spacer(1, 0.35 * inch))

    # Methodology (split into two paragraphs for readability)
    story.append(Paragraph("Methodology", h2_style))
    story.append(Paragraph(
        "This report was produced by a sequential multi-agent pipeline: "
        "(1) Taxonomy Architect — industry decomposition and TAM/SOM/CAGR; "
        "(2) Segment Specialist — primary/secondary segments per category; "
        "(3) Behavioral Ethologist — user pain points and friction; "
        "(4) Competitive Strategist — delivery mechanisms and gaps; "
        "(5) Decision Jury — conflict check, moat assessment, and resource allocation.",
        body,
    ))
    story.append(Paragraph("Data reflects agent-generated analysis based on the stated industry.", body))
    story.append(Spacer(1, 0.3 * inch))

    # Executive Summary — data-rich: industry, category count, key metrics, jury summary
    story.append(Paragraph("Executive Summary", h2_style))
    summary_parts = []
    summary_parts.append(f"<b>Scope:</b> This report analyzes the <b>{_esc(industry)}</b> market.")
    if categories:
        cat_names = ", ".join(_esc(c.get("name") or "") for c in categories[:8])
        if len(categories) > 8:
            cat_names += f" (and {len(categories) - 8} more)"
        summary_parts.append(f" The market is decomposed into <b>{len(categories)}</b> categories: {cat_names}.")
        # Add one line of high-level numbers if available
        first = categories[0]
        tam, som = first.get("tam") or "—", first.get("som") or "—"
        if tam != "—" or som != "—":
            summary_parts.append(f" Representative scale (first category): TAM {_esc(tam)}, SOM {_esc(som)}.")
    summary_parts.append(" " + (s1.get("summary") or "").strip().replace("\n", " ")[:400])
    if s1.get("summary") and len((s1.get("summary") or "")) > 400:
        summary_parts.append("…")
    jury_summary = _jury_str(jury, "executive_summary")
    if jury_summary:
        summary_parts.append(" <b>Key verdict:</b> " + _esc(jury_summary[:500]))
        if len(jury_summary) > 500:
            summary_parts.append("…")
    verdicts = jury.get("segment_verdicts") or []
    green = [v for v in verdicts if isinstance(v, dict) and _to_str_val(v.get("verdict")).lower() == "green"]
    if green:
        top = green[0]
        summary_parts.append(f" Top recommended segment: <b>{_esc(_to_str_val(top.get('category_name')))} / {_esc(_to_str_val(top.get('segment_name')))}</b>.")
    exec_text = "".join(summary_parts) if summary_parts else "No summary available."
    story.append(Paragraph(exec_text.replace("\n", "<br/>"), body))
    story.append(Spacer(1, 0.35 * inch))

    # Categories, Market Cap & Trends — table with Paragraph cells so text wraps
    story.append(Paragraph("Categories, Market Cap &amp; Trends", h2_style))
    if categories:
        # Column widths: give Trends enough space and wrap via Paragraph
        col_w = [1.0 * inch, 0.85 * inch, 0.85 * inch, 0.65 * inch, 0.65 * inch, 2.5 * inch]
        header_row = [
            Paragraph("<b>Category</b>", cell_header_style),
            Paragraph("<b>TAM</b>", cell_header_style),
            Paragraph("<b>SOM</b>", cell_header_style),
            Paragraph("<b>Hist. CAGR</b>", cell_header_style),
            Paragraph("<b>Proj. CAGR</b>", cell_header_style),
            Paragraph("<b>Trends</b>", cell_header_style),
        ]
        table_data = [header_row]
        for c in categories:
            trends_list = c.get("trends") or []
            trends_text = "<br/>".join(_esc(t) for t in trends_list) if trends_list else "—"
            table_data.append([
                Paragraph(_esc(c.get("name") or "—"), cell_style),
                Paragraph(_esc(c.get("tam") or "—"), cell_style),
                Paragraph(_esc(c.get("som") or "—"), cell_style),
                Paragraph(_esc(c.get("historical_cagr") or "—"), cell_style),
                Paragraph(_esc(c.get("projected_cagr") or "—"), cell_style),
                Paragraph(trends_text, cell_style),
            ])
        t = Table(table_data, colWidths=col_w)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No category data.", body))
    story.append(Spacer(1, 0.35 * inch))

    # Segmented Decomposition (drivers on new lines when multiple)
    story.append(Paragraph("Segmented Decomposition", h2_style))
    section2 = artifact.get("section2") or []
    for cs in section2:
        story.append(Paragraph(_esc(cs.get("category_name") or "Category"), h3_style))
        for seg in cs.get("segments") or []:
            name = _esc(seg.get("name") or "")
            seg_type = _esc(seg.get("segment_type") or "")
            drivers_list = seg.get("growth_drivers") or []
            drivers = "<br/>".join(_esc(d) for d in drivers_list) if drivers_list else "—"
            story.append(Paragraph(f"• <b>{name}</b> ({seg_type}):<br/>{drivers}", body))
        story.append(Spacer(1, 0.15 * inch))
    story.append(Spacer(1, 0.3 * inch))

    # User Pain Points & Friction (one paragraph per field, list items on new lines)
    story.append(Paragraph("User Pain Points &amp; Friction", h2_style))
    section3 = artifact.get("section3") or []
    for pp in section3:
        seg_title = f"{pp.get('category_name')} / {pp.get('segment_name')}"
        story.append(Paragraph(_esc(seg_title), h3_style))
        zmot = _esc(pp.get("zero_moment_of_truth") or "—")
        story.append(Paragraph(f"<b>Zero Moment of Truth:</b> {zmot}", body))
        alts = "<br/>".join(_esc(a) for a in (pp.get("alternative_paths") or []))
        story.append(Paragraph("<b>Alternative paths:</b><br/>" + (alts or "—"), body))
        killers = "<br/>".join(_esc(k) for k in (pp.get("retention_killers") or []))
        story.append(Paragraph("<b>Retention killers:</b><br/>" + (killers or "—"), body))
        story.append(Spacer(1, 0.15 * inch))
    story.append(Spacer(1, 0.3 * inch))

    # Competition, Delivery & Gaps
    story.append(Paragraph("Competition, Delivery &amp; Gaps", h2_style))
    section4 = artifact.get("section4") or []
    for cg in section4:
        seg_title = f"{cg.get('category_name')} / {cg.get('segment_name')}"
        story.append(Paragraph(_esc(seg_title), h3_style))
        story.append(Paragraph("<b>Delivery:</b> " + _esc(", ".join(cg.get("delivery_mechanisms") or []) or "—"), body))
        prod_gaps = "<br/>".join(_esc(g) for g in (cg.get("product_feature_gaps") or []))
        story.append(Paragraph("<b>Product gaps:</b><br/>" + (prod_gaps or "—"), body))
        exp_gaps = "<br/>".join(_esc(g) for g in (cg.get("experience_gaps") or []))
        story.append(Paragraph("<b>Experience gaps:</b><br/>" + (exp_gaps or "—"), body))
        story.append(Paragraph(f"<b>Moat:</b> {_esc(cg.get('moat_assessment') or '—')}", body))
        story.append(Spacer(1, 0.15 * inch))
    story.append(Spacer(1, 0.3 * inch))

    # Decision Jury — split long text into paragraphs by newline
    def _para_lines(text: str) -> None:
        raw = (text or "—").replace("&", "&amp;")
        for part in raw.split("\n"):
            part = part.strip()
            if part:
                story.append(Paragraph(part, body))

    story.append(Paragraph("Decision Jury", h2_style))
    story.append(Paragraph("Conflict Check", h3_style))
    _para_lines(_jury_str(jury, "conflict_check"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Moat Assessment", h3_style))
    _para_lines(_jury_str(jury, "moat_assessment"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Resource Allocation ($1M)", h3_style))
    _para_lines(_jury_str(jury, "resource_allocation"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Segment Verdicts", h3_style))
    for v in jury.get("segment_verdicts") or []:
        if not isinstance(v, dict):
            continue
        line = f"{_esc(_to_str_val(v.get('category_name')))} / {_esc(_to_str_val(v.get('segment_name')))}: <b>{_esc(_to_str_val(v.get('verdict')))}</b> — {_esc(_to_str_val(v.get('rationale')))}"
        story.append(Paragraph(line, body))

    doc.build(story)
    return buf.getvalue()


def build_html(artifact: dict[str, Any]) -> str:
    """Build an HTML report from the research artifact for in-browser view."""
    industry = artifact.get("industry") or "Market Research"
    s1 = artifact.get("section1") or {}
    jury = artifact.get("jury") or {}
    section2 = artifact.get("section2") or []
    section3 = artifact.get("section3") or []
    section4 = artifact.get("section4") or []

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Report: " + esc(industry) + "</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:2em auto;padding:0 1em;}",
        "h1{font-size:1.5rem;} h2{font-size:1.2rem;margin-top:1.5em;} h3{font-size:1rem;margin-top:1em;}",
        "table{border-collapse:collapse;width:100%;margin:0.5em 0;} th,td{border:1px solid #ccc;padding:6px;text-align:left;} th{background:#eee;}",
        "</style></head><body>",
        f"<h1>Market Research Report: {esc(industry)}</h1>",
        f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
        "<h2>Methodology</h2>",
        "<p>This report was produced by a sequential multi-agent pipeline: Taxonomy Architect, Segment Specialist, "
        "Behavioral Ethologist, Competitive Strategist, and Decision Jury.</p>",
        "<h2>Executive Summary</h2>",
    ]
    # Data-rich executive summary for HTML
    sum_parts = [f"<p><strong>Scope:</strong> This report analyzes the <strong>{esc(industry)}</strong> market."]
    cats = s1.get("categories") or []
    if cats:
        sum_parts.append(f" The market is decomposed into <strong>{len(cats)}</strong> categories: {esc(', '.join(c.get('name') or '' for c in cats[:8]))}.")
        first = cats[0]
        if first.get("tam") or first.get("som"):
            sum_parts.append(f" Representative scale (first category): TAM {esc(first.get('tam') or '—')}, SOM {esc(first.get('som') or '—')}.</p>")
        else:
            sum_parts.append("</p>")
    else:
        sum_parts.append("</p>")
    html_parts.append("".join(sum_parts))
    if s1.get("summary"):
        html_parts.append(f"<p>{esc((s1.get('summary') or '')[:500])}</p>")
    if _jury_str(jury, "executive_summary"):
        html_parts.append(f"<p><strong>Key verdict:</strong> {esc(_jury_str(jury, 'executive_summary')[:500])}</p>")
    verdicts = jury.get("segment_verdicts") or []
    green = [v for v in verdicts if isinstance(v, dict) and _to_str_val(v.get("verdict")).lower() == "green"]
    if green:
        top = green[0]
        html_parts.append(f"<p><strong>Top recommended segment:</strong> {esc(_to_str_val(top.get('category_name')))} / {esc(_to_str_val(top.get('segment_name')))}.</p>")
    if not (cats or s1.get("summary") or _jury_str(jury, "executive_summary")):
        html_parts.append("<p>No summary available.</p>")
    html_parts.append("<h2>Categories, Market Cap &amp; Trends</h2>")

    categories = s1.get("categories") or []
    if categories:
        html_parts.append("<table><tr><th>Category</th><th>TAM</th><th>SOM</th><th>Hist. CAGR</th><th>Proj. CAGR</th><th>Trends</th></tr>")
        for c in categories:
            trends_str = "; ".join(c.get("trends") or [])
            html_parts.append(
                f"<tr><td>{esc(c.get('name'))}</td><td>{esc(c.get('tam'))}</td><td>{esc(c.get('som'))}</td>"
                f"<td>{esc(c.get('historical_cagr'))}</td><td>{esc(c.get('projected_cagr'))}</td><td>{esc(trends_str)}</td></tr>"
            )
        html_parts.append("</table>")
    else:
        html_parts.append("<p>No category data.</p>")

    html_parts.append("<h2>Segmented Decomposition</h2>")
    for cs in section2:
        html_parts.append(f"<h3>{esc(cs.get('category_name'))}</h3><ul>")
        for seg in cs.get("segments") or []:
            drivers = "; ".join(seg.get("growth_drivers") or [])
            html_parts.append(f"<li><strong>{esc(seg.get('name'))}</strong> ({esc(seg.get('segment_type'))}): {esc(drivers)}</li>")
        html_parts.append("</ul>")

    html_parts.append("<h2>User Pain Points &amp; Friction</h2>")
    for pp in section3:
        html_parts.append(f"<h3>{esc(pp.get('category_name'))} / {esc(pp.get('segment_name'))}</h3>")
        html_parts.append(f"<p><strong>ZMOT:</strong> {esc(pp.get('zero_moment_of_truth'))}</p>")
        html_parts.append(f"<p><strong>Alternatives:</strong> {esc('; '.join(pp.get('alternative_paths') or []))}</p>")
        html_parts.append(f"<p><strong>Retention killers:</strong> {esc('; '.join(pp.get('retention_killers') or []))}</p>")

    html_parts.append("<h2>Competition, Delivery &amp; Gaps</h2>")
    for cg in section4:
        html_parts.append(f"<h3>{esc(cg.get('category_name'))} / {esc(cg.get('segment_name'))}</h3>")
        html_parts.append(f"<p>Delivery: {esc(', '.join(cg.get('delivery_mechanisms') or []))}</p>")
        html_parts.append(f"<p>Product gaps: {esc('; '.join(cg.get('product_feature_gaps') or []))}</p>")
        html_parts.append(f"<p>Experience gaps: {esc('; '.join(cg.get('experience_gaps') or []))}</p>")
        html_parts.append(f"<p>Moat: {esc(cg.get('moat_assessment'))}</p>")

    html_parts.append("<h2>Decision Jury</h2>")
    html_parts.append(f"<h3>Conflict Check</h3><p>{esc(_jury_str(jury, 'conflict_check'))}</p>")
    html_parts.append(f"<h3>Moat Assessment</h3><p>{esc(_jury_str(jury, 'moat_assessment'))}</p>")
    html_parts.append(f"<h3>Resource Allocation ($1M)</h3><p>{esc(_jury_str(jury, 'resource_allocation'))}</p>")
    html_parts.append("<h3>Segment Verdicts</h3><ul>")
    for v in jury.get("segment_verdicts") or []:
        if not isinstance(v, dict):
            continue
        html_parts.append(f"<li>{esc(_to_str_val(v.get('category_name')))} / {esc(_to_str_val(v.get('segment_name')))}: <strong>{esc(_to_str_val(v.get('verdict')))}</strong> — {esc(_to_str_val(v.get('rationale')))}</li>")
    html_parts.append("</ul></body></html>")

    return "".join(html_parts)
