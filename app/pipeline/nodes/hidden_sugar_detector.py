"""
app/pipeline/nodes/hidden_sugar_detector.py
---------------------------------------------
Layer 4B: Hidden Sugar Detection.

Detects sugar fraud patterns:
1. Sugar aliases in ingredients (50+ names for sugar)
2. Sugar splitting (same sugar listed under multiple names)
3. No Added Sugar claim violations
4. Artificial sweetener presence
5. High GI ingredients in diabetic/healthy claims
6. Total sugar load estimation from ingredients
"""

import re
import time
from pathlib import Path
import json

from app.pipeline.state import NutriGuardState
from app.core.logging import get_logger

logger = get_logger(__name__)

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "sugar_aliases.json"

with open(_DATA_PATH, "r") as f:
    _SUGAR_DATA = json.load(f)

SUGAR_ALIASES = [s.lower() for s in _SUGAR_DATA["sugar_aliases"]]
ARTIFICIAL_SWEETENERS = [s.lower() for s in _SUGAR_DATA["artificial_sweeteners"]]
HIGH_GI_INGREDIENTS = [s.lower() for s in _SUGAR_DATA["high_gi_ingredients"]]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _find_sugar_aliases_in_ingredients(ingredients_text: str) -> list[str]:
    """Find all sugar aliases present in ingredients list."""
    text_lower = _normalize(ingredients_text)
    found = []
    for alias in SUGAR_ALIASES:
        if alias in text_lower:
            found.append(alias)
    return found


def _detect_sugar_splitting(found_aliases: list[str]) -> dict:
    """
    Sugar splitting: listing the same sugar under 3+ different names
    to push each one lower in the ingredients order.
    This hides the true total sugar content.
    """
    if len(found_aliases) >= 3:
        return {
            "detected": True,
            "count": len(found_aliases),
            "aliases_found": found_aliases,
            "severity": "HIGH",
            "message": (
                f"Sugar splitting detected: {len(found_aliases)} different sugar aliases found "
                f"({', '.join(found_aliases[:5])}{'...' if len(found_aliases) > 5 else ''}). "
                f"Brands split sugar into multiple ingredients to push each lower "
                f"in the ingredients order, hiding true sugar load."
            ),
        }
    elif len(found_aliases) >= 2:
        return {
            "detected": True,
            "count": len(found_aliases),
            "aliases_found": found_aliases,
            "severity": "MEDIUM",
            "message": (
                f"Multiple sugar forms detected: {', '.join(found_aliases)}. "
                f"Combined sugar load may be higher than individual entries suggest."
            ),
        }
    return {"detected": False}


def _check_no_added_sugar_claim(
    claims: list,
    found_aliases: list[str],
    added_sugar_g: float,
) -> list[dict]:
    """
    Checks if 'no added sugar' claim is contradicted by:
    1. Sugar aliases in ingredients
    2. added_sugar_g > 0 in nutrition table
    """
    violations = []
    claims_lower = [_normalize(c) for c in claims]

    has_no_added_sugar_claim = any(
        "no added sugar" in c or "without added sugar" in c or
        "0g added sugar" in c or "zero added sugar" in c
        for c in claims_lower
    )

    if not has_no_added_sugar_claim:
        return []

    # Check nutrition table
    if added_sugar_g is not None and added_sugar_g > 0:
        violations.append({
            "type": "NO_ADDED_SUGAR_MATH_CONTRADICTION",
            "severity": "CRITICAL",
            "message": (
                f"Product claims 'no added sugar' but nutrition table "
                f"shows {added_sugar_g}g added sugar per 100g."
            ),
        })

    # Check ingredients for sugar aliases excluding naturally occurring ones
    naturally_occurring = {"lactose", "fructose", "glucose"}
    artificial_added = [
        a for a in found_aliases
        if a not in naturally_occurring
        and a not in ["honey", "dates", "raisins", "dried fruit"]  # debatable
    ]

    if artificial_added:
        violations.append({
            "type": "NO_ADDED_SUGAR_INGREDIENT_CONTRADICTION",
            "severity": "HIGH",
            "message": (
                f"Product claims 'no added sugar' but ingredients contain "
                f"added sugars: {', '.join(artificial_added[:5])}. "
                f"These are added sugars prohibited under FSSAI 'no added sugar' rules."
            ),
        })

    return violations


def _check_diabetic_friendly_claim(
    claims: list,
    found_aliases: list[str],
    high_gi_found: list[str],
    sugar_g: float,
) -> list[dict]:
    """Check diabetic friendly / suitable for diabetics claims."""
    violations = []
    claims_lower = [_normalize(c) for c in claims]

    diabetic_claims = [
        c for c in claims_lower
        if "diabetic" in c or "diabetes" in c or "sugar control" in c
        or "glycemic" in c or "low gi" in c
    ]

    if not diabetic_claims:
        return []

    if sugar_g is not None and sugar_g > 10:
        violations.append({
            "type": "DIABETIC_CLAIM_HIGH_SUGAR",
            "severity": "CRITICAL",
            "message": (
                f"Product makes diabetic-friendly claims but contains "
                f"{sugar_g}g sugar per 100g — inappropriate for diabetic consumers."
            ),
        })

    if high_gi_found:
        violations.append({
            "type": "DIABETIC_CLAIM_HIGH_GI_INGREDIENTS",
            "severity": "HIGH",
            "message": (
                f"Product makes diabetic-friendly claims but contains "
                f"high glycemic index ingredients: {', '.join(high_gi_found[:3])}."
            ),
        })

    return violations


def _check_artificial_sweeteners(
    claims: list,
    ingredients_text: str,
) -> list[dict]:
    """
    Detect artificial sweeteners and check for claim contradictions.
    """
    findings = []
    text_lower = _normalize(ingredients_text)
    claims_lower = [_normalize(c) for c in claims]

    found_sweeteners = [s for s in ARTIFICIAL_SWEETENERS if s in text_lower]

    if not found_sweeteners:
        return []

    # Natural claim + artificial sweetener = contradiction
    natural_claims = [
        c for c in claims_lower
        if "natural" in c or "no artificial" in c or "clean" in c
    ]

    if natural_claims:
        findings.append({
            "type": "NATURAL_CLAIM_ARTIFICIAL_SWEETENER",
            "severity": "HIGH",
            "sweeteners_found": found_sweeteners,
            "message": (
                f"Product makes 'natural' claims but contains artificial sweeteners: "
                f"{', '.join(found_sweeteners)}."
            ),
        })
    else:
        # Just informational
        findings.append({
            "type": "ARTIFICIAL_SWEETENER_PRESENT",
            "severity": "INFO",
            "sweeteners_found": found_sweeteners,
            "message": (
                f"Artificial sweeteners detected: {', '.join(found_sweeteners)}. "
                f"Not suitable for consumers avoiding artificial sweeteners."
            ),
        })

    return findings


def _estimate_sugar_position(ingredients_text: str, found_aliases: list[str]) -> dict:
    """
    Check if sugar appears in first 3 ingredients (high quantity indicator).
    FSSAI requires ingredients listed in descending order by weight.
    """
    if not ingredients_text or not found_aliases:
        return {}

    # Split ingredients by common delimiters
    ingredients_list = re.split(r'[,;]', ingredients_text)
    ingredients_list = [i.strip().lower() for i in ingredients_list if i.strip()]

    sugar_positions = []
    for i, ingredient in enumerate(ingredients_list[:10]):
        for alias in found_aliases:
            if alias in ingredient:
                sugar_positions.append({
                    "position": i + 1,
                    "ingredient": ingredient,
                    "alias_matched": alias,
                })
                break

    high_position_sugars = [s for s in sugar_positions if s["position"] <= 3]

    if high_position_sugars:
        return {
            "detected": True,
            "sugar_in_top_3": high_position_sugars,
            "severity": "HIGH",
            "message": (
                f"Sugar appears in top 3 ingredients by weight: "
                f"{', '.join(s['ingredient'] for s in high_position_sugars)}. "
                f"This product is predominantly sugar by composition."
            ),
        }

    return {"detected": False, "sugar_positions": sugar_positions}


async def hidden_sugar_detector_node(state: NutriGuardState) -> dict:
    """
    Layer 4B: Hidden sugar detection.

    Scans ingredients for 50+ sugar aliases, detects sugar splitting,
    checks claim contradictions, and estimates true sugar load.
    """
    logger.info("hidden_sugar_detector.start")
    start_time = time.time()

    extraction = state.get("extraction_result", {})

    if not extraction:
        return {
            "hidden_sugar_result": {
                "analysed": False,
                "note": "No extraction data available",
            }
        }

    ingredients_text = extraction.get("ingredients")
    if isinstance(ingredients_text, list):
        ingredients_text = ", ".join(str(i) for i in ingredients_text)
    claims = extraction.get("claims", [])
    product_name = extraction.get("product_name", "Unknown")
    nutrients_per_100g = extraction.get("nutrients_per_100g", {})
    added_sugar_g = nutrients_per_100g.get("added_sugar_g")
    sugar_g = nutrients_per_100g.get("sugar_g")

    if not ingredients_text:
        logger.warning("hidden_sugar_detector.no_ingredients", product=product_name)
        return {
            "hidden_sugar_result": {
                "analysed": False,
                "note": "Ingredients list not visible. Cannot detect hidden sugars.",
                "product": product_name,
            }
        }

    # Run all checks
    found_aliases = _find_sugar_aliases_in_ingredients(ingredients_text)
    high_gi_found = [
        ing for ing in HIGH_GI_INGREDIENTS
        if ing in _normalize(ingredients_text)
    ]

    sugar_splitting = _detect_sugar_splitting(found_aliases)
    sugar_position = _estimate_sugar_position(ingredients_text, found_aliases)
    no_added_sugar_violations = _check_no_added_sugar_claim(
        claims, found_aliases, added_sugar_g
    )
    diabetic_violations = _check_diabetic_friendly_claim(
        claims, found_aliases, high_gi_found, sugar_g
    )
    sweetener_findings = _check_artificial_sweeteners(claims, ingredients_text)

    all_violations = no_added_sugar_violations + diabetic_violations + [
        f for f in sweetener_findings if f.get("severity") != "INFO"
    ]

    elapsed_ms = round((time.time() - start_time) * 1000)

    logger.info(
        "hidden_sugar_detector.complete",
        product=product_name,
        sugar_aliases_found=len(found_aliases),
        violations=len(all_violations),
        sugar_splitting=sugar_splitting.get("detected", False),
        elapsed_ms=elapsed_ms,
    )

    return {
        "hidden_sugar_result": {
            "analysed": True,
            "product": product_name,
            "sugar_aliases_found": found_aliases,
            "sugar_alias_count": len(found_aliases),
            "sugar_splitting": sugar_splitting,
            "sugar_position_analysis": sugar_position,
            "high_gi_ingredients": high_gi_found,
            "artificial_sweeteners": sweetener_findings,
            "violations": all_violations,
            "has_violations": len(all_violations) > 0,
            "summary": {
                "total_sugar_aliases": len(found_aliases),
                "splitting_detected": sugar_splitting.get("detected", False),
                "violations_count": len(all_violations),
                "high_gi_count": len(high_gi_found),
            }
        }
    }