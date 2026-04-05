"""
app/pipeline/nodes/ingredient_parser.py
-----------------------------------------
Layer 4: Ingredient Parser.

Analyzes the ingredients list to detect:
1. High-concern INS/E-number additives
2. Hidden allergens
3. "Natural" claim contradictions
4. Claim-ingredient contradictions (e.g. "No MSG" but contains INS 635)
"""

import json
import re
import time
from pathlib import Path

from app.pipeline.state import NutriGuardState
from app.core.logging import get_logger

logger = get_logger(__name__)

_ADDITIVES_PATH = Path(__file__).parent.parent.parent / "data" / "ins_additives.json"

with open(_ADDITIVES_PATH, "r") as f:
    _ADDITIVES_DATA = json.load(f)

ADDITIVES_DB = _ADDITIVES_DATA["additives"]
ALLERGENS_LIST = _ADDITIVES_DATA["allergens"]
NATURAL_VIOLATIONS = _ADDITIVES_DATA["natural_claim_violations"]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _find_ins_codes(ingredients_text: str) -> list[dict]:
    """
    Finds all INS/E-number codes in ingredients text.
    Handles all formats found on Indian food labels:
    - INS 635, INS635, (INS 102)
    - E211, E500ii
    - 503(ii), 471, 472e, 322(i)  — standalone in brackets
    - [503(ii), 471 & 472e]       — square bracket lists
    """
    found = []
    detected_keys = set()

    # Format 1: "INS 635", "INS635", "(INS 102)"
    for match in re.finditer(r'\bINS\s*(\d+[a-zA-Z]{0,3})\b', ingredients_text, re.IGNORECASE):
        key = f"INS {match.group(1).upper()}"
        if key in ADDITIVES_DB and key not in detected_keys:
            detected_keys.add(key)
            found.append({"code": key, "data": ADDITIVES_DB[key]})

    # Format 2: "E211", "E500ii"
    for match in re.finditer(r'\bE(\d{3,4}[a-zA-Z]{0,3})\b', ingredients_text):
        key = f"INS {match.group(1).upper()}"
        if key in ADDITIVES_DB and key not in detected_keys:
            detected_keys.add(key)
            found.append({"code": key, "data": ADDITIVES_DB[key]})

    # Format 3: Standalone codes — "503(ii)", "471", "472e", "322(i)"
    # Extract number + optional letter suffix + optional roman numeral in parens
    for match in re.finditer(r'\b(\d{3,4})([a-zA-Z]{0,2})?(?:\(([ivxIVX]{1,3})\))?', ingredients_text):
        num = match.group(1)
        letter = (match.group(2) or "").lower()
        roman = (match.group(3) or "").lower()
        
        # Build candidate keys to try
        candidates = [
            f"INS {num}{letter}{roman}".upper().strip(),
            f"INS {num}{roman}".upper().strip(),
            f"INS {num}{letter}".upper().strip(),
            f"INS {num}".upper().strip(),
        ]
        
        for key in candidates:
            if key in ADDITIVES_DB and key not in detected_keys:
                detected_keys.add(key)
                found.append({"code": key, "data": ADDITIVES_DB[key]})
                break

    # Format 4: Alias matching — "Sodium Benzoate", "MSG", "Tartrazine"
    for code, data in ADDITIVES_DB.items():
        if code in detected_keys:
            continue
        for alias in data.get("aliases", []):
            if alias.lower() in ingredients_text.lower():
                detected_keys.add(code)
                found.append({"code": code, "data": data})
                break

    return found

def _check_natural_claims(claims: list, ingredients_text: str) -> list[dict]:
    """
    Checks if any 'natural' or 'no artificial' claims are contradicted
    by the ingredients list.
    """
    violations = []
    natural_claims = [
        c for c in claims
        if any(kw in c.lower() for kw in ["natural", "no artificial", "clean", "pure", "real"])
    ]

    if not natural_claims:
        return []

    for violation_term in NATURAL_VIOLATIONS:
        if violation_term.lower() in ingredients_text.lower():
            for claim in natural_claims:
                violations.append({
                    "type": "NATURAL_CLAIM_CONTRADICTION",
                    "claim": claim,
                    "contradicting_ingredient": violation_term,
                    "severity": "HIGH",
                    "message": (
                        f"Claim '{claim}' is contradicted by ingredient '{violation_term}' "
                        f"which is artificial/synthetic."
                    ),
                })

    return violations


def _check_allergens(ingredients_text: str, declared_allergens: str = "") -> list[dict]:
    """
    Scans ingredients for common allergens.
    Returns list of detected allergens for transparency.
    """
    found_allergens = []
    text_lower = ingredients_text.lower()

    for allergen in ALLERGENS_LIST:
        if allergen.lower() in text_lower:
            found_allergens.append(allergen)

    if found_allergens:
        return [{
            "type": "ALLERGEN_PRESENCE",
            "allergens_detected": list(set(found_allergens)),
            "severity": "INFO",
            "message": (
                f"Allergens detected in ingredients: {', '.join(set(found_allergens))}. "
                f"Verify these are properly declared on the label."
            ),
        }]
    return []


def _check_claim_ingredient_contradictions(
    claims: list,
    ins_found: list,
    ingredients_text: str,
) -> list[dict]:
    """
    Checks for specific claim vs ingredient contradictions.
    e.g. "No MSG" but contains INS 635 (MSG family)
    """
    violations = []
    claims_lower = [_normalize(c) for c in claims]

    # "No MSG" but contains MSG-family additives
    msg_free_claim = any("no msg" in c or "msg free" in c for c in claims_lower)
    msg_codes = {"INS 621", "INS 627", "INS 631", "INS 635"}
    found_msg_codes = [i["code"] for i in ins_found if i["code"] in msg_codes]

    if msg_free_claim and found_msg_codes:
        violations.append({
            "type": "CLAIM_INGREDIENT_CONTRADICTION",
            "claim": "No MSG",
            "contradicting_ingredients": found_msg_codes,
            "severity": "CRITICAL",
            "message": (
                f"Product claims 'No MSG' but contains MSG-family additives: "
                f"{', '.join(found_msg_codes)}"
            ),
        })

    # "No Preservatives" but contains preservatives
    no_preservative_claim = any(
        "no preservative" in c or "preservative free" in c for c in claims_lower
    )
    preservative_codes = [
        i["code"] for i in ins_found
        if i["data"].get("type") == "Preservative"
    ]
    if no_preservative_claim and preservative_codes:
        violations.append({
            "type": "CLAIM_INGREDIENT_CONTRADICTION",
            "claim": "No Preservatives",
            "contradicting_ingredients": preservative_codes,
            "severity": "CRITICAL",
            "message": (
                f"Product claims 'No Preservatives' but contains: "
                f"{', '.join(preservative_codes)}"
            ),
        })

    # "No Artificial Colours" but contains artificial colour INS codes
    no_colour_claim = any(
        "no artificial colour" in c or "no artificial color" in c
        or "no added colour" in c for c in claims_lower
    )
    colour_codes = [
        i["code"] for i in ins_found
        if i["data"].get("type") == "Artificial Colour"
    ]
    if no_colour_claim and colour_codes:
        violations.append({
            "type": "CLAIM_INGREDIENT_CONTRADICTION",
            "claim": "No Artificial Colours",
            "contradicting_ingredients": colour_codes,
            "severity": "CRITICAL",
            "message": (
                f"Product claims 'No Artificial Colours' but contains: "
                f"{', '.join(colour_codes)}"
            ),
        })

    return violations


async def ingredient_parser_node(state: NutriGuardState) -> dict:
    """
    Layer 4: Ingredient analysis for additive detection,
    allergen scanning, and claim contradiction checking.
    """
    logger.info("ingredient_parser.start")
    start_time = time.time()

    extraction = state.get("extraction_result", {})

    if not extraction:
        return {
            "ingredient_result": {
                "analysed": False,
                "note": "No extraction data available",
            }
        }

    ingredients_text = extraction.get("ingredients")
    if isinstance(ingredients_text, list):
        ingredients_text = ", ".join(str(i) for i in ingredients_text)
    claims = extraction.get("claims", [])
    product_name = extraction.get("product_name", "Unknown")
    

    if not ingredients_text:
        logger.warning("ingredient_parser.no_ingredients", product=product_name)
        return {
            "ingredient_result": {
                "analysed": False,
                "note": "Ingredients list not visible on label image. Cannot analyse.",
                "product": product_name,
            }
        }

    # Run all checks
    ins_found = _find_ins_codes(ingredients_text)
    natural_violations = _check_natural_claims(claims, ingredients_text)
    allergen_info = _check_allergens(ingredients_text)
    claim_contradictions = _check_claim_ingredient_contradictions(
        claims, ins_found, ingredients_text
    )

    # Build additive report
    high_concern = [i for i in ins_found if i["data"]["concern"] == "HIGH"]
    medium_concern = [i for i in ins_found if i["data"]["concern"] == "MEDIUM"]
    low_concern = [i for i in ins_found if i["data"]["concern"] == "LOW"]

    all_violations = natural_violations + claim_contradictions
    has_violations = len(all_violations) > 0

    elapsed_ms = round((time.time() - start_time) * 1000)
    logger.info(
        "ingredient_parser.complete",
        product=product_name,
        ins_codes_found=len(ins_found),
        high_concern=len(high_concern),
        violations=len(all_violations),
        elapsed_ms=elapsed_ms,
    )

    return {
        "ingredient_result": {
            "analysed": True,
            "product": product_name,
            "additives": {
                "total_found": len(ins_found),
                "high_concern": [
                    {
                        "code": i["code"],
                        "name": i["data"]["name"],
                        "type": i["data"]["type"],
                        "concern": "HIGH",
                        "notes": i["data"]["notes"],
                    }
                    for i in high_concern
                ],
                "medium_concern": [
                    {
                        "code": i["code"],
                        "name": i["data"]["name"],
                        "type": i["data"]["type"],
                        "concern": "MEDIUM",
                        "notes": i["data"]["notes"],
                    }
                    for i in medium_concern
                ],
                "low_concern": [
                    {
                        "code": i["code"],
                        "name": i["data"]["name"],
                        "type": i["data"]["type"],
                        "concern": "LOW",
                        "notes": i["data"]["notes"],
                    }
                    for i in low_concern
                ],
            },
            "allergens": allergen_info,
            "violations": all_violations,
            "has_violations": has_violations,
        }
    }