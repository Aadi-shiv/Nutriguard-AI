"""
app/reports/pdf_builder.py
Common PDF building utilities shared across all complaint templates.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ── Brand Colors ───────────────────────────────────────────────
COLOR_PRIMARY    = HexColor("#1a1a2e")   # dark navy
COLOR_CRITICAL   = HexColor("#c0392b")   # red
COLOR_WARNING    = HexColor("#e67e22")   # orange
COLOR_SAFE       = HexColor("#27ae60")   # green
COLOR_LIGHT_GRAY = HexColor("#f5f5f5")
COLOR_MID_GRAY   = HexColor("#cccccc")
COLOR_DARK_GRAY  = HexColor("#555555")


def get_styles():
    """Return all paragraph styles used across templates."""
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title",
            fontSize=20,
            fontName="Helvetica-Bold",
            textColor=COLOR_PRIMARY,
            spaceAfter=6,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=11,
            fontName="Helvetica",
            textColor=COLOR_DARK_GRAY,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=white,
            spaceBefore=12,
            spaceAfter=6,
            leftIndent=8,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10,
            fontName="Helvetica",
            textColor=black,
            spaceAfter=4,
            leading=15,
            alignment=TA_JUSTIFY,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=black,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            fontSize=8,
            fontName="Helvetica",
            textColor=COLOR_DARK_GRAY,
            spaceAfter=2,
        ),
        "violation_title": ParagraphStyle(
            "violation_title",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=COLOR_CRITICAL,
            spaceAfter=2,
        ),
        "legal": ParagraphStyle(
            "legal",
            fontSize=9,
            fontName="Helvetica-Oblique",
            textColor=COLOR_DARK_GRAY,
            spaceAfter=4,
            leading=14,
            alignment=TA_JUSTIFY,
        ),
        "right": ParagraphStyle(
            "right",
            fontSize=10,
            fontName="Helvetica",
            alignment=TA_RIGHT,
            spaceAfter=4,
        ),
    }
    return styles


def section_header(text: str, color: HexColor, styles: dict):
    """Returns a colored section header as a Table."""
    data = [[Paragraph(text, styles["section_header"])]]
    table = Table(data, colWidths=[17 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [color]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def violation_table(violations: list, styles: dict):
    """Renders a table of violations with regulation citations."""
    if not violations:
        return Paragraph("No violations found.", styles["body"])

    rows = [["#", "Claim", "Verdict", "Regulation", "Details"]]
    for i, v in enumerate(violations, 1):
        rows.append([
            str(i),
            v.get("claim", "")[:30],
            v.get("verdict", ""),
            (v.get("regulation") or v.get("regulation_citation") or "—")[:40],
            v.get("reason", "")[:80],
        ])

    col_widths = [1*cm, 3*cm, 2.5*cm, 4*cm, 6.5*cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  COLOR_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [COLOR_LIGHT_GRAY, white]),
        ("GRID",          (0, 0), (-1, -1), 0.5, COLOR_MID_GRAY),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("TEXTCOLOR",     (2, 1), (2, -1),  COLOR_CRITICAL),
    ]))
    return table


def fraud_score_table(score: int, level: str, styles: dict):
    """Renders a prominent fraud score box."""
    color = COLOR_CRITICAL if score >= 70 else (
        COLOR_WARNING if score >= 40 else COLOR_SAFE
    )

    score_style = ParagraphStyle(
        "score",
        fontSize=36,
        fontName="Helvetica-Bold",
        textColor=white,
        alignment=TA_CENTER,
    )
    label_style = ParagraphStyle(
        "label",
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=white,
        alignment=TA_CENTER,
    )

    data = [[
        Paragraph(f"{score} / 100", score_style),
        Paragraph(f"FRAUD SCORE\n{level}", label_style),
    ]]
    table = Table(data, colWidths=[5*cm, 12*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def build_pdf(filepath: str, elements: list):
    """Build the final PDF from flowable elements."""
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    doc.build(elements)