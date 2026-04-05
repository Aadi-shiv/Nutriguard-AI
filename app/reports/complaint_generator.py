"""
app/reports/complaint_generator.py
Main entry point for generating complaint PDFs.
Routes to correct template based on fraud score.
"""

from datetime import date
from pathlib import Path

from app.reports.pdf_builder import build_pdf
from app.reports.templates.advisory import build_advisory
from app.reports.templates.complaint import build_complaint
from app.reports.templates.urgent import build_urgent
from app.core.logging import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("./reports_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_complaint(
    report: dict,
    user_info: dict = None,
) -> dict:
    """
    Generate appropriate PDF based on fraud score.

    Args:
        report: Final report dict from report_aggregator_node
        user_info: Optional dict with name, address, phone, store, purchase_date

    Returns:
        dict with filepath, tier, and status
    """
    if user_info is None:
        user_info = {}

    # Add today's date if not provided
    if "date" not in user_info:
        user_info["date"] = date.today().strftime("%d %B %Y")

    fraud = report.get("fraud_score", {})
    score = fraud.get("score", 0)
    product = report.get("product_name", "unknown_product")
    safe_name = product.replace(" ", "_").lower()[:30]

    # Route to correct tier
    if score <= 20:
        logger.info("complaint_generator.no_complaint", score=score)
        return {
            "generated": False,
            "reason": "Fraud score too low — product is mostly clean",
            "score": score,
            "filepath": None,
        }

    elif score <= 39:
        tier = "advisory"
        elements = build_advisory(report, user_info)
        filename = f"nutriguard_advisory_{safe_name}.pdf"

    elif score <= 69:
        tier = "complaint"
        elements = build_complaint(report, user_info)
        filename = f"nutriguard_complaint_{safe_name}.pdf"

    else:
        tier = "urgent"
        elements = build_urgent(report, user_info)
        filename = f"nutriguard_URGENT_{safe_name}.pdf"

    filepath = OUTPUT_DIR / filename
    build_pdf(str(filepath), elements)

    logger.info(
        "complaint_generator.complete",
        tier=tier,
        score=score,
        filepath=str(filepath),
    )

    return {
        "generated": True,
        "tier": tier,
        "score": score,
        "filepath": str(filepath),
        "filename": filename,
    }