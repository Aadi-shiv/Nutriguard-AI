"""
app/reports/templates/complaint.py
Formal FSSAI Complaint Letter — for fraud score 40-69.
Formal language, regulation citations, violation proof.
"""

from reportlab.platypus import Paragraph, Spacer, HRFlowable
from reportlab.lib.units import cm

from app.reports.pdf_builder import (
    get_styles, section_header, fraud_score_table,
    violation_table, COLOR_CRITICAL, COLOR_PRIMARY,
    COLOR_WARNING, COLOR_DARK_GRAY
)


def build_complaint(report: dict, user_info: dict) -> list:
    """Returns list of flowable elements for formal complaint PDF."""
    styles = get_styles()
    elements = []

    fraud = report.get("fraud_score", {})
    layer_results = report.get("layer_results", {})
    regulatory = layer_results.get("regulatory_compliance", {})
    math_val = layer_results.get("math_validation", {})
    rag = layer_results.get("rag_compliance", {})

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

    # Math violations
    math_failures = math_val.get("failures", [])

    # ── Header ─────────────────────────────────────────────────
    elements.append(Paragraph("NutriGuard AI", styles["title"]))
    elements.append(Paragraph(
        "Formal Complaint to Food Safety and Standards Authority of India",
        styles["subtitle"]
    ))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY))
    elements.append(Spacer(1, 0.3*cm))

    # Addressee
    elements.append(Paragraph("To,", styles["body"]))
    elements.append(Paragraph("<b>The Food Safety Commissioner</b>", styles["body"]))
    elements.append(Paragraph(
        "Food Safety and Standards Authority of India (FSSAI)<br/>"
        "FDA Bhawan, Kotla Road, New Delhi — 110002<br/>"
        "Email: fssai@nic.in | Helpline: 1800-11-4420",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Complainant
    elements.append(Paragraph(
        f"<b>From:</b> {user_info.get('name', 'Consumer')}",
        styles["body"]
    ))
    elements.append(Paragraph(
        f"<b>Address:</b> {user_info.get('address', 'Not provided')}",
        styles["body"]
    ))
    elements.append(Paragraph(
        f"<b>Date:</b> {user_info.get('date', 'Today')}",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Subject
    elements.append(Paragraph(
        f"<b>Subject: Formal complaint regarding misleading nutritional claims "
        f"on {product}</b>",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_DARK_GRAY))
    elements.append(Spacer(1, 0.3*cm))

    # Fraud Score
    elements.append(fraud_score_table(score, fraud.get("level", ""), styles))
    elements.append(Spacer(1, 0.4*cm))

    # Product Details
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

    # Body of complaint
    elements.append(section_header("COMPLAINT STATEMENT", COLOR_PRIMARY, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        f"I, {user_info.get('name', 'the undersigned consumer')}, wish to formally "
        f"bring to your attention certain labelling violations found on the above "
        f"mentioned product. An automated analysis conducted via NutriGuard AI — "
        f"a mathematical nutritional fraud detection system — has identified "
        f"{len(all_violations)} violations of FSSAI Labelling Regulations 2020.",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Violations Table
    elements.append(section_header("VIOLATIONS FOUND", COLOR_CRITICAL, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(violation_table(all_violations, styles))
    elements.append(Spacer(1, 0.3*cm))

    # Math proof if any
    if math_failures:
        elements.append(section_header("MATHEMATICAL PROOF", COLOR_WARNING, styles))
        elements.append(Spacer(1, 0.2*cm))
        for f in math_failures:
            elements.append(Paragraph(
                f"• {f.get('check', '')}: {f.get('message', '')}",
                styles["body"]
            ))
        elements.append(Spacer(1, 0.3*cm))

    # Requested Action
    elements.append(section_header("REQUESTED ACTION", COLOR_PRIMARY, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "I respectfully request FSSAI to:",
        styles["body"]
    ))
    actions = [
        "Investigate the labelling practices of the above product",
        "Direct the manufacturer to correct all misleading claims",
        "Ensure compliance with FSSAI Labelling Regulations 2020",
        "Issue appropriate penalties as per FSS Act 2006",
    ]
    for action in actions:
        elements.append(Paragraph(f"• {action}", styles["body"]))
    elements.append(Spacer(1, 0.3*cm))

    # Legal basis
    elements.append(section_header("LEGAL BASIS", COLOR_PRIMARY, styles))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "This complaint is filed under the Food Safety and Standards Act 2006, "
        "Section 26 (Responsibilities of food business operators) and "
        "FSSAI Labelling Regulations 2020. Penalties for misleading claims "
        "range from Rs. 1 lakh to Rs. 10 lakh under Schedule II of the FSS Act.",
        styles["legal"]
    ))
    elements.append(Spacer(1, 0.4*cm))

    # Signature
    elements.append(Paragraph(
        f"Yours sincerely,<br/><br/>"
        f"<b>{user_info.get('name', '________________')}</b><br/>"
        f"{user_info.get('address', '')}<br/>"
        f"{user_info.get('phone', '')}",
        styles["body"]
    ))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_DARK_GRAY))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "Generated by NutriGuard AI | Automated Nutritional Fraud Detection System | "
        "Analysis is mathematical and reproducible",
        styles["small"]
    ))

    return elements