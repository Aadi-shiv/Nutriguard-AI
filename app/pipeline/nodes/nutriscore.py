"""
app/pipeline/nodes/nutriscore.py
---------------------------------
Layer 3: NutriScore 2024 Algorithm.

Official algorithm from Santé Publique France (January 2024 update).
Scores products A-E based on negative (unhealthy) and
positive (healthy) nutrient points.

Source: https://www.santepubliquefrance.fr/nutri-score
"""

import time
from app.pipeline.state import NutriGuardState
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── NutriScore 2024 Scoring Tables ────────────────────────────────────────────
# All values are per 100g

ENERGY_POINTS = [
    (335, 0), (670, 1), (1005, 2), (1340, 3), (1675, 4),
    (2010, 5), (2345, 6), (2680, 7), (3015, 8), (3350, 9),
]  # kcal thresholds → if energy > threshold, points = value + 1

SUGAR_POINTS = [
    (3.4, 0), (6.8, 1), (10, 2), (14, 3), (17, 4),
    (20, 5), (24, 6), (27, 7), (31, 8), (34, 9),
    (37, 10), (40, 11), (43, 12), (46, 13), (48, 14),
]  # 2024 update: stricter thresholds, max 15 points

SAT_FAT_POINTS = [
    (1, 0), (2, 1), (3, 2), (4, 3), (5, 4),
    (6, 5), (7, 6), (8, 7), (9, 8), (10, 9),
]

SODIUM_POINTS = [
    (90, 0), (180, 1), (270, 2), (360, 3), (450, 4),
    (540, 5), (630, 6), (720, 7), (810, 8), (900, 9),
    (990, 10), (1080, 11), (1170, 12), (1260, 13), (1350, 14),
    (1440, 15), (1530, 16), (1620, 17), (1710, 18), (1800, 19),
]  # 2024 update: stricter, max 20 points

FIBER_POINTS = [
    (3.0, 1), (4.1, 2), (5.2, 3), (6.3, 4), (7.4, 5),
]

PROTEIN_POINTS = [
    (2.4, 1), (4.8, 2), (7.2, 3), (9.6, 4), (12.0, 5),
]

# NutriScore 2024 grade boundaries
GRADE_BOUNDARIES = [
    (-float('inf'), -1, 'A'),
    (-1, 2, 'B'),
    (2, 10, 'C'),
    (10, 18, 'D'),
    (18, float('inf'), 'E'),
]


def _lookup_points(value: float, table: list[tuple]) -> int:
    """
    Looks up points for a given value using a threshold table.
    Returns max points if value exceeds all thresholds.
    """
    if value is None:
        return 0
    points = 0
    for threshold, pts in table:
        if value > threshold:
            points = pts + 1
        else:
            break
    return min(points, len(table))


def _calculate_energy_points(energy_kcal: float) -> int:
    """Convert kcal to kJ then look up points."""
    if energy_kcal is None:
        return 0
    energy_kj = energy_kcal * 4.184
    return _lookup_points(energy_kj, ENERGY_POINTS)


def _get_grade(score: int) -> str:
    """Convert final NutriScore score to grade A-E."""
    if score <= -1:
        return 'A'
    elif score <= 2:
        return 'B'
    elif score <= 10:
        return 'C'
    elif score <= 18:
        return 'D'
    else:
        return 'E'


def _grade_color(grade: str) -> str:
    colors = {'A': 'Dark Green', 'B': 'Light Green', 'C': 'Yellow', 'D': 'Orange', 'E': 'Red'}
    return colors.get(grade, 'Unknown')


async def nutriscore_engine_node(state: NutriGuardState) -> dict:
    """
    Layer 3: NutriScore 2024 calculation.

    Computes negative points (N) from energy, sugar, saturated fat, sodium.
    Computes positive points (P) from fiber and protein.

    Critical 2024 rule: if N >= 11, protein points = 0.
    This prevents high-protein junk food from gaming the score.
    """
    logger.info("nutriscore_engine.start")
    start_time = time.time()

    extraction = state.get("extraction_result", {})

    if not extraction or extraction.get("_stub"):
        logger.warning("nutriscore_engine.no_extraction_data")
        return {
            "nutriscore_result": {
                "grade": "UNKNOWN",
                "score": None,
                "note": "No extraction data available",
                "_stub": True,
            }
        }

    nutrients = extraction.get("nutrients_per_100g", {})
    product_name = extraction.get("product_name", "Unknown")

    if not nutrients:
        logger.warning("nutriscore_engine.no_nutrients", product=product_name)
        return {
            "nutriscore_result": {
                "grade": "UNKNOWN",
                "score": None,
                "note": "No per-100g nutrient data available",
            }
        }

    # ── Negative Points (unhealthy nutrients) ─────────────────────────────────
    energy_pts = _calculate_energy_points(nutrients.get("energy_kcal"))
    sugar_pts = _lookup_points(nutrients.get("sugar_g", 0), SUGAR_POINTS)
    sat_fat_pts = _lookup_points(nutrients.get("saturated_fat_g", 0), SAT_FAT_POINTS)
    sodium_pts = _lookup_points(nutrients.get("sodium_mg", 0), SODIUM_POINTS)

    N = energy_pts + sugar_pts + sat_fat_pts + sodium_pts

    # ── Positive Points (healthy nutrients) ───────────────────────────────────
    fiber_pts = _lookup_points(nutrients.get("fiber_g", 0), FIBER_POINTS)
    protein_pts_raw = _lookup_points(nutrients.get("protein_g", 0), PROTEIN_POINTS)

    # Critical 2024 rule: if N >= 11, protein points do not count
    # This prevents high-protein junk food from gaming the system
    if N >= 11:
        protein_pts = 0
        protein_rule_applied = True
    else:
        protein_pts = protein_pts_raw
        protein_rule_applied = False

    P = fiber_pts + protein_pts

    # ── Final Score and Grade ─────────────────────────────────────────────────
    score = N - P
    grade = _get_grade(score)

    elapsed_ms = round((time.time() - start_time) * 1000)
    logger.info(
        "nutriscore_engine.complete",
        product=product_name,
        grade=grade,
        score=score,
        N=N,
        P=P,
        elapsed_ms=elapsed_ms,
    )

    return {
        "nutriscore_result": {
            "grade": grade,
            "color": _grade_color(grade),
            "score": score,
            "negative_points": {
                "total": N,
                "breakdown": {
                    "energy": energy_pts,
                    "sugar": sugar_pts,
                    "saturated_fat": sat_fat_pts,
                    "sodium": sodium_pts,
                }
            },
            "positive_points": {
                "total": P,
                "breakdown": {
                    "fiber": fiber_pts,
                    "protein": protein_pts,
                    "protein_raw": protein_pts_raw,
                }
            },
            "protein_rule_applied": protein_rule_applied,
            "protein_rule_note": (
                "Protein points set to 0 because N >= 11 (2024 rule). "
                "High-protein products with poor overall nutrition cannot use protein to improve score."
                if protein_rule_applied else None
            ),
            "nutrients_used": {
                "energy_kcal_per_100g": nutrients.get("energy_kcal"),
                "sugar_g_per_100g": nutrients.get("sugar_g"),
                "saturated_fat_g_per_100g": nutrients.get("saturated_fat_g"),
                "sodium_mg_per_100g": nutrients.get("sodium_mg"),
                "fiber_g_per_100g": nutrients.get("fiber_g"),
                "protein_g_per_100g": nutrients.get("protein_g"),
            },
        }
    }