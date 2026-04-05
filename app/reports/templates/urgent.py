"""
app/reports/templates/urgent.py
Urgent FSSAI Complaint — for fraud score 70-100.
Strongest legal language, full mathematical proof,
demands product recall, CC to consumer court.
"""

from reportlab.platypus import Paragraph, Spacer, HRFlowable
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor

from app.reports.pdf_builder import (
    get_styles, section_header, fraud_score_table,
    violation_table, COLOR_CRITICAL, COLOR_PRIMARY,
    COLOR_WARNING, COLOR_DARK_GRAY, COLOR_LIGHT_GRAY
)


def build_urgent(report: dict, user_info: dict) -> list:
    """Returns list of flowable elements for urgent complaint PDF."""
    styles = get_styles()
    elements = []

    fraud = report.get("fraud_score", {})
    layer_results = report.get("layer_results", {})
    regulatory = layer_results.get("regulatory_compliance", {})
    math_val = layer_results.get("math_validation", {})
    rag = layer_results.get("rag_compliance", {})
    nutriscore = layer_results.get("nutriscore", {})
    hidden_sugar = layer_results.get("hidden_sugar", {})

    product = report.get("product_name", "Unknown Product")
    score = fraud.get("score", 0)
    signals = fraud.get("signals", [])

    # Collect all violations
    all_violations = []
    for v in regulatory.get("claim_verdicts", []):
        if v.get("verdict") == "NON_COMPLIANT":
            all_violations.append(v)
    for v in rag.get("rag_verdicts", []):
        if v.get("verdict") == "NON_COMPLIANT":
            all_violations.append(v)

    math_failures = math_val.get("failures", [])
    sugar_violations = hidden_sugar.get("violations", [])

    # ── URGENT Banner ───────────────────────────────────────────
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    urgent_style = ParagraphStyle(
        "urgent",
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=HexColor("#ffffff"),
        alignment=TA_CENTER,
    )
    banner_data = [[Paragraph(
        "⚠ URGENT — CRITICAL FOOD SAFETY COMPLAINT ⚠", urgent_style
    )]]
    banner = Table(banner_data, colWidths=[17*cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_CRITICAL),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 0.3*cm))

    # Header
    elements.append(Paragraph("NutriGuard AI", styles["title"]))
    elements.append(Paragraph(
        "Urgent Formal Complaint — Food Safety and Standards Authority of India",
        styles["subtitle"]
    ))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_CRITICAL))
    elements.append(Spacer(1, 0.3*cm))

    # CC Block
    elements.append(Paragraph("<b>To,</b>", styles["body"]))
    elements.append(Paragraph(
        "The Food Safety Commissioner<br/>"
        "Food Safety and Standards Authority of India (FSSAI)<br/>"
        "FDA Bhawan, Kotla Road, New Delhi — 110002<br/>"
        "Email: fssai@nic.in | Helpline: 1800-11-4420",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("<b>CC:</b>", styles["body"]))
    elements.append(Paragraph(
        "The District Consumer Forum<br/>"
        "National Consumer Helpline: 1800-11-4000<br/>"
        "State Food Safety Commissioner",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Complainant
    elements.append(Paragraph(
        f"<b>Complainant:</b> {user_info.get('name', 'Consumer')}<br/>"
        f"<b>Address:</b> {user_info.get('address', 'Not provided')}<br/>"
        f"<b>Phone:</b> {user_info.get('phone', 'Not provided')}<br/>"
        f"<b>Date:</b> {user_info.get('date', 'Today')}",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_DARK_GRAY))
    elements.append(Spacer(1, 0.3*cm))

    # Fraud Score
    elements.append(fraud_score_table(score, fraud.get("level", ""), styles))
    elements.append(Spacer(1, 0.4*cm))

    # Product
    elements.append(section_header("PRODUCT DETAILS", COLOR_PRIMARY, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(f"<b>Product Name:</b> {product}", styles["body"]))
    elements.append(Paragraph(
        f"<b>Purchased From:</b> {user_info.get('store', 'Not specified')}",
        styles["body"]
    ))
    elements.append(Paragraph(
        f"<b>Purchase Date:</b> {user_info.get('purchase_date', 'Not specified')}",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Statement
    elements.append(section_header("URGENT COMPLAINT STATEMENT", COLOR_CRITICAL, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        f"I, {user_info.get('name', 'the undersigned')} hereby lodge an URGENT formal "
        f"complaint against the manufacturer of <b>{product}</b> for serious violations "
        f"of the Food Safety and Standards Act 2006 and FSSAI Labelling Regulations 2020. "
        f"NutriGuard AI — a mathematical nutritional fraud detection system — has identified "
        f"a fraud score of <b>{score}/100 (CRITICAL)</b> based on {len(all_violations)} "
        f"regulatory violations and {len(math_failures)} mathematical proof failures. "
        f"This product poses a risk of consumer deception and demands immediate regulatory action.",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Violations
    elements.append(section_header(
        f"REGULATORY VIOLATIONS ({len(all_violations)} FOUND)",
        COLOR_CRITICAL, styles
    ))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(violation_table(all_violations, styles))
    elements.append(Spacer(1, 0.3*cm))

    # Math proof
    if math_failures:
        elements.append(section_header(
            "MATHEMATICAL PROOF OF FRAUD", COLOR_WARNING, styles
        ))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph(
            "The following Atwater calorie calculations prove numerical fraud "
            "in the nutrition table:",
            styles["body"]
        ))
        for f in math_failures:
            elements.append(Paragraph(
                f"• <b>{f.get('check', '')}:</b> {f.get('message', '')}",
                styles["body"]
            ))
        elements.append(Spacer(1, 0.3*cm))

    # Hidden sugar
    if sugar_violations:
        elements.append(section_header("HIDDEN SUGAR VIOLATIONS", COLOR_WARNING, styles))
        elements.append(Spacer(1, 0.2*cm))
        for v in sugar_violations:
            elements.append(Paragraph(f"• {v.get('message', '')}", styles["body"]))
        elements.append(Spacer(1, 0.3*cm))

    # NutriScore
    grade = nutriscore.get("grade", "?")
    elements.append(section_header("NUTRISCORE EVIDENCE", COLOR_PRIMARY, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        f"Independent NutriScore 2024 analysis assigned this product "
        f"Grade <b>{grade}</b> — indicating poor nutritional quality — "
        f"while the product makes positive health claims on its label.",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Demanded actions
    elements.append(section_header("DEMANDED ACTIONS", COLOR_CRITICAL, styles))
    elements.append(Spacer(1, 0.2*cm))
    actions = [
        "Immediate investigation of the manufacturer's labelling practices",
        "Suspension of sale of this product pending investigation",
        "Mandatory product recall if violations are confirmed",
        "Correction of all misleading nutritional claims on the label",
        "Imposition of maximum penalties under FSS Act 2006 Section 52-53",
        "Public notification of the violations found",
        "Inspection of manufacturer's other product lines",
    ]
    for action in actions:
        elements.append(Paragraph(f"• {action}", styles["body"]))
    elements.append(Spacer(1, 0.3*cm))

    # Legal basis
    elements.append(section_header("LEGAL BASIS", COLOR_PRIMARY, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "This complaint is filed under:<br/>"
        "• Food Safety and Standards Act 2006, Section 26, 52, 53<br/>"
        "• FSSAI Labelling and Display Regulations 2020<br/>"
        "• Schedule II, Regulation 2.4 — Nutritional Claims<br/>"
        "• Consumer Protection Act 2019, Section 2(9) — Misleading Advertisements<br/>"
        "Penalties range from Rs. 1 lakh to Rs. 10 lakh and/or imprisonment "
        "for misleading food labelling under the FSS Act.",
        styles["legal"]
    ))
    elements.append(Spacer(1, 0.4*cm))

    # Signature
    elements.append(Paragraph(
        f"Yours faithfully,<br/><br/>"
        f"<b>{user_info.get('name', '________________')}</b><br/>"
        f"{user_info.get('address', '')}<br/>"
        f"{user_info.get('phone', '')}",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_DARK_GRAY))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "Generated by NutriGuard AI | Mathematical fraud score is fully reproducible | "
        "All calculations available on request",
        styles["small"]
    ))

    return elements