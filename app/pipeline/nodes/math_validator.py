"""
app/pipeline/nodes/math_validator.py
--------------------------------------
Layer 1: Mathematical verification engine.

Performs 3 checks:
1. Atwater calorie cross-check
2. Per-serving vs per-100g consistency
3. Serving size manipulation detection
"""

import time
from app.pipeline.state import NutriGuardState
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Atwater Factors ───────────────────────────────────────────
FAT_KCAL_PER_G = 9
PROTEIN_KCAL_PER_G = 4
CARB_KCAL_PER_G = 4
FIBER_KCAL_PER_G = 2  # fiber offset (indigestible)

# ── Tolerance Thresholds ──────────────────────────────────────
CALORIE_TOLERANCE_PCT = 10   # allow 10% deviation in calorie check
NUTRIENT_TOLERANCE_PCT = 15  # allow 15% deviation in per-100g consistency

# ── Realistic Serving Size Ranges (grams) ────────────────────
SERVING_SIZE_RANGES = {
    "default": (5, 250),
}


def _pct_error(stated: float, calculated: float) -> float:
    """Returns percentage error between stated and calculated values."""
    if calculated == 0:
        return 0.0
    return abs(stated - calculated) / calculated * 100


def _check_atwater_calories(nutrients: dict, section: str) -> list[dict]:
    """
    Check 1: Atwater Calorie Cross-Check.
    Calculates expected calories from macronutrients and
    compares against stated calories.
    """
    failures = []

    energy = nutrients.get("energy_kcal")
    protein = nutrients.get("protein_g")
    carbs = nutrients.get("carbohydrate_g")
    fat = nutrients.get("fat_g")
    fiber = nutrients.get("fiber_g", 0) or 0

    # Skip if any required value is missing
    if any(v is None for v in [energy, protein, carbs, fat]):
        return []

    calculated = (
        (fat * FAT_KCAL_PER_G) +
        (carbs * CARB_KCAL_PER_G) +
        (protein * PROTEIN_KCAL_PER_G) -
        (fiber * FIBER_KCAL_PER_G)
    )

    error_pct = _pct_error(energy, calculated)

    if error_pct > CALORIE_TOLERANCE_PCT:
        severity = "CRITICAL" if error_pct > 50 else "HIGH" if error_pct > 25 else "MEDIUM"
        failures.append({
            "check": "ATWATER_CALORIE",
            "section": section,
            "stated_kcal": energy,
            "calculated_kcal": round(calculated, 2),
            "error_pct": round(error_pct, 2),
            "severity": severity,
            "message": (
                f"Stated {energy} kcal but macronutrients calculate to "
                f"{round(calculated, 2)} kcal ({round(error_pct, 1)}% error)"
            ),
        })

    return failures


def _check_per100g_consistency(
    per_serving: dict,
    per_100g: dict,
    serving_size_g: float,
) -> list[dict]:
    """
    Check 2: Per-serving vs per-100g consistency.
    If both are provided, verifies that per_serving = per_100g * serving_size / 100.
    """
    failures = []

    if not per_serving or not per_100g or not serving_size_g:
        return []

    nutrients_to_check = [
        "energy_kcal", "protein_g", "carbohydrate_g",
        "fat_g", "sugar_g", "fiber_g", "sodium_mg",
    ]

    for nutrient in nutrients_to_check:
        val_serving = per_serving.get(nutrient)
        val_100g = per_100g.get(nutrient)

        if val_serving is None or val_100g is None:
            continue
        if val_100g == 0 and val_serving == 0:
            continue

        # Expected per-serving value based on per-100g
        expected_serving = val_100g * serving_size_g / 100
        error_pct = _pct_error(val_serving, expected_serving)

        if error_pct > NUTRIENT_TOLERANCE_PCT:
            severity = "CRITICAL" if error_pct > 50 else "HIGH" if error_pct > 25 else "MEDIUM"
            failures.append({
                "check": "PER100G_CONSISTENCY",
                "nutrient": nutrient,
                "stated_per_serving": val_serving,
                "expected_per_serving": round(expected_serving, 3),
                "per_100g_value": val_100g,
                "serving_size_g": serving_size_g,
                "error_pct": round(error_pct, 2),
                "severity": severity,
                "message": (
                    f"{nutrient}: stated {val_serving} per serving but "
                    f"per-100g value implies {round(expected_serving, 2)} "
                    f"({round(error_pct, 1)}% error)"
                ),
            })

    return failures


def _check_serving_size(serving_size_g: float, product_name: str) -> list[dict]:
    """
    Check 3: Serving size manipulation detection.
    Flags unrealistically small serving sizes used to hide nutrients.
    """
    failures = []

    if serving_size_g is None:
        return []

    min_serving, max_serving = SERVING_SIZE_RANGES["default"]

    if serving_size_g < min_serving:
        failures.append({
            "check": "SERVING_SIZE_MANIPULATION",
            "stated_serving_g": serving_size_g,
            "minimum_realistic_g": min_serving,
            "severity": "HIGH",
            "message": (
                f"Serving size {serving_size_g}g is suspiciously small. "
                f"May be used to hide nutrient levels via rounding."
            ),
        })
    elif serving_size_g > max_serving:
        failures.append({
            "check": "SERVING_SIZE_UNUSUALLY_LARGE",
            "stated_serving_g": serving_size_g,
            "maximum_realistic_g": max_serving,
            "severity": "LOW",
            "message": (
                f"Serving size {serving_size_g}g is unusually large."
            ),
        })

    return failures


async def math_validator_node(state: NutriGuardState) -> dict:
    """
    Layer 1: Mathematical verification of nutritional label data.

    Runs 3 deterministic checks and returns all failures with
    exact numbers and percentage errors as evidence.
    """
    logger.info("math_validator.start")
    start_time = time.time()

    extraction = state.get("extraction_result", {})

    if not extraction or extraction.get("_stub"):
        logger.warning("math_validator.no_extraction_data")
        return {
            "math_validation_result": {
                "passed": True,
                "failures": [],
                "checks_run": 0,
                "note": "No extraction data available",
            }
        }

    per_serving = extraction.get("nutrients_per_serving", {})
    per_100g = extraction.get("nutrients_per_100g", {})
    serving_size_g = extraction.get("serving_size_g")
    product_name = extraction.get("product_name", "Unknown")

    all_failures = []

    # Run Check 1: Atwater on per-serving values
    if per_serving:
        failures = _check_atwater_calories(per_serving, "per_serving")
        all_failures.extend(failures)

    # Run Check 1 also on per-100g values
    if per_100g:
        failures = _check_atwater_calories(per_100g, "per_100g")
        all_failures.extend(failures)

    # Run Check 2: Per-serving vs per-100g consistency
    if per_serving and per_100g and serving_size_g:
        failures = _check_per100g_consistency(per_serving, per_100g, serving_size_g)
        all_failures.extend(failures)

    # Run Check 3: Serving size manipulation
    failures = _check_serving_size(serving_size_g, product_name)
    all_failures.extend(failures)

    passed = len(all_failures) == 0
    elapsed_ms = round((time.time() - start_time) * 1000)

    logger.info(
        "math_validator.complete",
        product=product_name,
        checks_run=3,
        failures=len(all_failures),
        passed=passed,
        elapsed_ms=elapsed_ms,
    )

    return {
        "math_validation_result": {
            "passed": passed,
            "failures": all_failures,
            "checks_run": 3,
            "product": product_name,
            "serving_size_g": serving_size_g,
        }
    }