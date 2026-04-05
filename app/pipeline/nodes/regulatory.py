"""
app/pipeline/nodes/regulatory.py
----------------------------------
Layer 2: FSSAI 2020 Regulatory Compliance Engine.

For each claim on the front label, checks whether the actual
nutrient values (per 100g) meet the official FSSAI threshold.

Returns a verdict for each claim: COMPLIANT, NON_COMPLIANT, or UNVERIFIABLE.
"""

import json
import time
from pathlib import Path

from app.pipeline.state import NutriGuardState
from app.core.logging import get_logger

logger = get_logger(__name__)

# Load FSSAI thresholds from data file
_THRESHOLDS_PATH = Path(__file__).parent.parent.parent / "data" / "fssai_thresholds.json"

with open(_THRESHOLDS_PATH, "r") as f:
    _FSSAI_DATA = json.load(f)

CLAIM_THRESHOLDS = _FSSAI_DATA["claim_thresholds"]


def _normalize_claim(claim: str) -> str:
    """Lowercase and strip a claim string for matching."""
    return claim.lower().strip()


def _match_claim_to_rule(claim: str) -> tuple[str | None, dict | None]:
    """
    Finds the matching FSSAI rule for a given claim string.
    Also handles quantity-style claims like '10g PROTEIN' or '3g FIBER'.
    """
    claim_lower = _normalize_claim(claim)

    # Direct alias matching
    for rule_key, rule in CLAIM_THRESHOLDS.items():
        aliases = [a.lower() for a in rule.get("aliases", [])]
        for alias in aliases:
            if alias in claim_lower or claim_lower in alias:
                return rule_key, rule

    # Quantity-style claim matching e.g. "10g protein" → "source of protein"
    # Maps keywords in claim to rule keys
    quantity_keyword_map = {
        "protein": "source of protein",
        "fiber": "source of fiber",
        "fibre": "source of fiber",
        "trans fat": "zero trans fat",
        "trans-fat": "zero trans fat",
        "sugar": "low sugar",
        "fat": "low fat",
        "sodium": "low sodium",
        "calorie": "low calorie",
        "calories": "low calorie",
    }   
    for keyword, rule_key in quantity_keyword_map.items():
        if keyword in claim_lower:
            # Only match if it looks like a quantity claim (contains a number)
            has_number = any(c.isdigit() for c in claim_lower)
            if has_number:
                return rule_key, CLAIM_THRESHOLDS.get(rule_key)

    return None, None


def _evaluate_claim(
    claim: str,
    rule: dict,
    nutrients_per_100g: dict,
) -> dict:
    """
    Evaluates a single claim against its FSSAI rule.

    Returns a verdict dict with full evidence.
    """
    nutrient_key = rule["nutrient"]
    operator = rule["operator"]
    threshold = rule["threshold"]
    actual_value = nutrients_per_100g.get(nutrient_key)

    # Cannot verify if nutrient value is missing
    if actual_value is None:
        return {
            "claim": claim,
            "verdict": "UNVERIFIABLE",
            "reason": f"Nutrient '{nutrient_key}' not found in label data",
            "regulation": rule["regulation"],
            "threshold": threshold,
            "actual_value": None,
            "unit": rule["unit"],
        }

    # Evaluate against threshold
    if operator == ">=":
        compliant = actual_value >= threshold
        margin = actual_value - threshold
    elif operator == "<=":
        compliant = actual_value <= threshold
        margin = threshold - actual_value
    elif operator == "==":
        compliant = actual_value == threshold
        margin = threshold - actual_value
    else:
        compliant = False
        margin = 0

    verdict = "COMPLIANT" if compliant else "NON_COMPLIANT"

    # Build human-readable reason
    if compliant:
        reason = (
            f"Actual {actual_value}{rule['unit'].split('/')[0]} per 100g "
            f"{'meets' if operator == '>=' else 'is within'} "
            f"threshold of {threshold}{rule['unit'].split('/')[0]} "
            f"(margin: {round(abs(margin), 3)})"
        )
    else:
        reason = (
            f"Claim '{claim}' is NON-COMPLIANT: "
            f"actual {actual_value}{rule['unit'].split('/')[0]} per 100g "
            f"does not meet FSSAI threshold of {threshold}{rule['unit'].split('/')[0]} "
            f"(shortfall: {round(abs(margin), 3)})"
        )

    return {
        "claim": claim,
        "verdict": verdict,
        "reason": reason,
        "regulation": rule["regulation"],
        "threshold": threshold,
        "threshold_operator": operator,
        "actual_value": actual_value,
        "unit": rule["unit"],
        "margin": round(abs(margin), 3),
    }
def _check_mandatory_warnings(nutrients_per_100g: dict) -> list[dict]:
    """
    Checks nutrients that must be flagged regardless of claims.
    These are mandatory warnings based on FSSAI nutrient thresholds.
    """
    warnings = []

    # High saturated fat warning
    sat_fat = nutrients_per_100g.get("saturated_fat_g")
    if sat_fat is not None and sat_fat > 1.5:
        warnings.append({
            "claim": "MANDATORY_CHECK: Saturated Fat",
            "verdict": "NON_COMPLIANT",
            "reason": (
                f"Saturated fat is {sat_fat}g per 100g. "
                f"FSSAI threshold for safe level: ≤1.5g/100g. "
                f"This product contains {round(sat_fat/1.5, 1)}x the safe limit. "
                f"Product should not make any heart health or cholesterol claims."
            ),
            "regulation": "FSSAI Schedule II, Regulation 2.4",
            "threshold": 1.5,
            "threshold_operator": "<=",
            "actual_value": sat_fat,
            "unit": "g/100g",
            "margin": round(sat_fat - 1.5, 2),
            "mandatory": True,
        })

    # High sodium warning
    sodium = nutrients_per_100g.get("sodium_mg")
    if sodium is not None and sodium > 600:
        warnings.append({
            "claim": "MANDATORY_CHECK: Sodium",
            "verdict": "NON_COMPLIANT",
            "reason": (
                f"Sodium is {sodium}mg per 100g which is HIGH. "
                f"FSSAI high sodium threshold: >600mg/100g."
            ),
            "regulation": "FSSAI Schedule II, Regulation 2.4",
            "threshold": 600,
            "threshold_operator": "<=",
            "actual_value": sodium,
            "unit": "mg/100g",
            "margin": round(sodium - 600, 2),
            "mandatory": True,
        })

    # High sugar warning
    sugar = nutrients_per_100g.get("sugar_g")
    if sugar is not None and sugar > 22.5:
        warnings.append({
            "claim": "MANDATORY_CHECK: Sugar",
            "verdict": "NON_COMPLIANT",
            "reason": (
                f"Sugar is {sugar}g per 100g which is HIGH. "
                f"FSSAI high sugar threshold: >22.5g/100g."
            ),
            "regulation": "FSSAI Schedule II, Regulation 2.4",
            "threshold": 22.5,
            "threshold_operator": "<=",
            "actual_value": sugar,
            "unit": "g/100g",
            "margin": round(sugar - 22.5, 2),
            "mandatory": True,
        })

    return warnings


async def regulatory_engine_node(state: NutriGuardState) -> dict:
    """
    Layer 2: FSSAI 2020 compliance checker.

    Checks every front-label claim against official thresholds.
    """
    logger.info("regulatory_engine.start")
    start_time = time.time()

    extraction = state.get("extraction_result", {})

    if not extraction or extraction.get("_stub"):
        logger.warning("regulatory_engine.no_extraction_data")
        return {
            "regulatory_result": {
                "claim_verdicts": [],
                "overall_compliant": True,
                "note": "No extraction data available",
            }
        }

    claims = extraction.get("claims", [])
    nutrients_per_100g = extraction.get("nutrients_per_100g", {})
    product_name = extraction.get("product_name", "Unknown")

    if not claims:
        logger.info("regulatory_engine.no_claims_found", product=product_name)
        return {
            "regulatory_result": {
                "claim_verdicts": [],
                "overall_compliant": True,
                "note": "No front-label claims found to verify",
            }
        }

    
    verdicts = []

    # Always run mandatory nutrient warnings first
    mandatory_warnings = _check_mandatory_warnings(nutrients_per_100g)
    verdicts.extend(mandatory_warnings)
    unmatched_claims = []

    for claim in claims:
        rule_key, rule = _match_claim_to_rule(claim)

        if rule is None:
            unmatched_claims.append(claim)
            verdicts.append({
                "claim": claim,
                "verdict": "UNVERIFIABLE",
                "reason": "No matching FSSAI regulation found for this claim type",
                "regulation": None,
            })
            continue

        verdict = _evaluate_claim(claim, rule, nutrients_per_100g)
        verdicts.append(verdict)

        logger.info(
            "regulatory_engine.claim_checked",
            claim=claim,
            verdict=verdict["verdict"],
            actual=verdict.get("actual_value"),
            threshold=verdict.get("threshold"),
        )

    # Overall compliance
    non_compliant = [v for v in verdicts if v["verdict"] == "NON_COMPLIANT"]
    overall_compliant = len(non_compliant) == 0

    elapsed_ms = round((time.time() - start_time) * 1000)
    logger.info(
        "regulatory_engine.complete",
        product=product_name,
        total_claims=len(claims),
        compliant=len([v for v in verdicts if v["verdict"] == "COMPLIANT"]),
        non_compliant=len(non_compliant),
        unverifiable=len([v for v in verdicts if v["verdict"] == "UNVERIFIABLE"]),
        elapsed_ms=elapsed_ms,
    )

    return {
        "regulatory_result": {
            "claim_verdicts": verdicts,
            "overall_compliant": overall_compliant,
            "summary": {
                "total_claims": len(claims),
                "compliant": len([v for v in verdicts if v["verdict"] == "COMPLIANT"]),
                "non_compliant": len(non_compliant),
                "unverifiable": len([v for v in verdicts if v["verdict"] == "UNVERIFIABLE"]),
                "unmatched_claims": unmatched_claims,
            },
        }
    }