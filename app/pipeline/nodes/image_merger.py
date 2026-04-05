"""
app/pipeline/nodes/image_merger.py
------------------------------------
Handles single, dual, and triple image inputs.

Single image:  passes through to vision node
Dual image:    front (claims) + back (nutrition + ingredients)
Triple image:  front (claims) + back (nutrition) + ingredients (ingredients only)
"""

import base64
import json
import time

from groq import Groq

from app.pipeline.state import NutriGuardState
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ExtractionError

logger = get_logger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

FRONT_PROMPT = """You are a food label expert. This is the FRONT of an Indian packaged food product.

Extract ONLY the marketing claims and product identity. Return ONLY valid JSON, no markdown.

{
  "product_name": "full product name",
  "brand": "brand name",
  "fssai_license": "FSSAI number if visible, else null",
  "claims": ["every", "marketing", "claim", "visible"],
  "serving_size_g": <serving size in grams if visible anywhere on front label, else null>,
  "servings_per_pack": null,
  "ingredients": null,
  "nutrients_per_serving": {},
  "nutrients_per_100g": {},
  "label_language": "English/Hindi/Both/Other",
  "extraction_notes": "any notes"
}"""

BACK_PROMPT = """You are a food label expert. This is the BACK of an Indian packaged food product.

Extract the nutrition table and ingredients list. Return ONLY valid JSON, no markdown.

{
  "product_name": null,
  "brand": null,
  "fssai_license": "FSSAI number if visible, else null",
  "claims": [],
  "serving_size_g": <number or null>,
  "servings_per_pack": <number or null>,
  "ingredients": "full ingredients text",
  "nutrients_per_serving": {
    "energy_kcal": <number or null>,
    "protein_g": <number or null>,
    "carbohydrate_g": <number or null>,
    "sugar_g": <number or null>,
    "added_sugar_g": <number or null>,
    "fat_g": <number or null>,
    "saturated_fat_g": <number or null>,
    "trans_fat_g": <number or null>,
    "fiber_g": <number or null>,
    "sodium_mg": <number or null>,
    "calcium_mg": <number or null>,
    "iron_mg": <number or null>
  },
  "nutrients_per_100g": {
    "energy_kcal": <number or null>,
    "protein_g": <number or null>,
    "carbohydrate_g": <number or null>,
    "sugar_g": <number or null>,
    "added_sugar_g": <number or null>,
    "fat_g": <number or null>,
    "saturated_fat_g": <number or null>,
    "trans_fat_g": <number or null>,
    "fiber_g": <number or null>,
    "sodium_mg": <number or null>,
    "calcium_mg": <number or null>,
    "iron_mg": <number or null>
  },
  "label_language": "English/Hindi/Both/Other",
  "extraction_notes": "any notes"
}"""

NUTRITION_ONLY_PROMPT = """You are a food label expert. This image shows the nutrition facts table of an Indian packaged food product.

Extract ONLY the nutrition values. Return ONLY valid JSON, no markdown, no backticks.

{
  "serving_size_g": <number or null>,
  "servings_per_pack": <number or null>,
  "nutrients_per_serving": {
    "energy_kcal": <number or null>,
    "protein_g": <number or null>,
    "carbohydrate_g": <number or null>,
    "sugar_g": <number or null>,
    "added_sugar_g": <number or null>,
    "fat_g": <number or null>,
    "saturated_fat_g": <number or null>,
    "trans_fat_g": <number or null>,
    "fiber_g": <number or null>,
    "sodium_mg": <number or null>,
    "calcium_mg": <number or null>,
    "iron_mg": <number or null>
  },
  "nutrients_per_100g": {
    "energy_kcal": <number or null>,
    "protein_g": <number or null>,
    "carbohydrate_g": <number or null>,
    "sugar_g": <number or null>,
    "added_sugar_g": <number or null>,
    "fat_g": <number or null>,
    "saturated_fat_g": <number or null>,
    "trans_fat_g": <number or null>,
    "fiber_g": <number or null>,
    "sodium_mg": <number or null>,
    "calcium_mg": <number or null>,
    "iron_mg": <number or null>
  },
  "extraction_notes": "any notes about extraction quality"
}

CRITICAL RULES:
- nutrients_per_serving = values for ONE serving (small amounts, e.g. energy ~60-120 kcal for a biscuit serving)
- nutrients_per_100g = values per 100 grams (larger amounts, e.g. energy ~400-500 kcal for biscuits)
- If the label only shows per 100g values, put them in nutrients_per_100g and leave nutrients_per_serving null
- If the label only shows per serving values, put them in nutrients_per_serving and leave nutrients_per_100g null
- NEVER put per-100g values in nutrients_per_serving field
- serving_size_g is always a small number like 15, 17, 20, 30 — never 100"""
INGREDIENTS_ONLY_PROMPT = """You are a food label expert. This image shows the ingredients list of an Indian packaged food product.

Extract the full ingredients text as a single string exactly as written on the label.
Return ONLY valid JSON, no markdown, no backticks.

{
  "ingredients": "paste full ingredients text here as one single string",
  "fssai_license": "FSSAI number if visible or null",
  "extraction_notes": "any notes"
}

IMPORTANT: ingredients must be a single string, not a list or array."""


def _extract_from_image(image_bytes: bytes, prompt: str, label: str) -> dict:
    """Extract data from a single image using Groq."""
    from app.pipeline.nodes.vision import _detect_image_type

    media_type = _detect_image_type(image_bytes)
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
            },
            {"type": "text", "text": prompt},
        ],
    }]

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=2048,
        temperature=0,
        messages=messages,
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])
    

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"image_merger.json_parse_failed.{label}", error=str(e))
        # Retry once
        logger.warning(f"image_merger.retry_{label}")
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1500,
            temperature=0,
            messages=messages,
        )
        raw_text = response.choices[0].message.content.strip()
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1])
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            raise ExtractionError(f"Failed to parse {label} image JSON after retry", {})
def _extract_with_consensus(
    image_bytes: bytes,
    prompt: str,
    label: str,
    runs: int = 5,
) -> dict:
    """
    Extract nutrition data multiple times and return
    median values for each nutrient field.
    Eliminates LLM non-determinism for numeric extraction.
    """
    results = []

    for i in range(runs):
        try:
            data = _extract_from_image(image_bytes, prompt, label)
            if data is not None:
                results.append(data)
            else:
                logger.warning(f"image_merger.consensus_run_{i+1}_none", label=label)
            logger.info(
                f"image_merger.consensus_run_{i+1}",
                label=label,
                has_energy=bool(
                    data.get("nutrients_per_100g", {}).get("energy_kcal") or
                    data.get("nutrients_per_serving", {}).get("energy_kcal")
                ),
            )
        except Exception as e:
            logger.warning(f"image_merger.consensus_run_{i+1}_failed", error=str(e))
        
        # Small delay to avoid rate limiting
        if i < runs - 1:
            time.sleep(0.3)

    if not results:
        raise ExtractionError(f"All {runs} consensus runs failed for {label}", {})

    if len(results) == 1:
        logger.warning("image_merger.consensus_only_one_result", label=label)
        return results[0]

    # Take median for all numeric nutrient fields
    nutrient_keys = [
        "energy_kcal", "protein_g", "carbohydrate_g",
        "sugar_g", "added_sugar_g", "fat_g",
        "saturated_fat_g", "trans_fat_g", "fiber_g",
        "sodium_mg", "calcium_mg", "iron_mg"
    ]

    merged = results[0].copy()

    for section in ["nutrients_per_serving", "nutrients_per_100g"]:
        section_merged = {}
        for key in nutrient_keys:
            values = [
                r.get(section, {}).get(key)
                for r in results
                if r.get(section, {}) and r.get(section, {}).get(key) is not None
            ]
            if values:
                sorted_vals = sorted(values)
                section_merged[key] = sorted_vals[len(sorted_vals) // 2]
            else:
                section_merged[key] = None
        merged[section] = section_merged

    # Serving size — median
    serving_values = [
        r.get("serving_size_g")
        for r in results
        if r.get("serving_size_g") is not None
    ]
    if serving_values:
        sorted_serving = sorted(serving_values)
        merged["serving_size_g"] = sorted_serving[len(sorted_serving) // 2]

    logger.info(
        "image_merger.consensus_complete",
        label=label,
        runs_successful=len(results),
        runs_total=runs,
        median_energy=merged.get("nutrients_per_100g", {}).get("energy_kcal") or
                      merged.get("nutrients_per_serving", {}).get("energy_kcal"),
    )

    return merged        
def _validate_nutrients(nutrients_per_100g: dict, nutrients_per_serving: dict, serving_size_g: float) -> dict:
    """
    Validates extracted nutrients by cross-checking per-serving vs per-100g.
    If per-100g values look wrong, recalculates from per-serving.
    """
    if not serving_size_g or serving_size_g <= 0:
        return nutrients_per_100g

    validated = dict(nutrients_per_100g)

    for key in ["energy_kcal", "protein_g", "carbohydrate_g", "sugar_g",
                "fat_g", "saturated_fat_g", "fiber_g", "sodium_mg"]:
        per_100g = nutrients_per_100g.get(key)
        per_serving = nutrients_per_serving.get(key)

        if per_serving is not None and per_100g is not None:
            expected_per_100g = (per_serving / serving_size_g) * 100
            deviation = abs(per_100g - expected_per_100g) / (expected_per_100g + 0.001)
            if deviation > 0.5:
                validated[key] = round(expected_per_100g, 2)

    return validated

def _merge_extractions(front: dict, back: dict) -> dict:
    """
    Merges front and back label extractions.
    Front provides: product_name, brand, claims
    Back provides: nutrition data, ingredients, serving size
    """
    merged = {
        "product_name": front.get("product_name") or back.get("product_name"),
        "brand": front.get("brand") or back.get("brand"),
        "fssai_license": front.get("fssai_license") or back.get("fssai_license"),
        "claims": front.get("claims", []),
        "serving_size_g": back.get("serving_size_g"),
        "servings_per_pack": back.get("servings_per_pack"),
        "ingredients": back.get("ingredients"),
        "nutrients_per_serving": back.get("nutrients_per_serving", {}),
        "nutrients_per_100g": back.get("nutrients_per_100g", {}),
        "label_language": front.get("label_language", "English"),
        "extraction_notes": f"Front: {front.get('extraction_notes', '')} | Back: {back.get('extraction_notes', '')}",
        "validation_issues": [],
        "extraction_confidence": "HIGH",
        "dual_image": True,
        "triple_image": False,
    }
    serving_size = merged.get("serving_size_g")
    per_100g = merged.get("nutrients_per_100g", {})
    per_serving = merged.get("nutrients_per_serving", {})

    # If per_100g is all null but per_serving has values, calculate per_100g
    has_100g_values = any(v is not None for v in per_100g.values()) if per_100g else False
    has_serving_values = any(v is not None for v in per_serving.values()) if per_serving else False

    if not has_100g_values and has_serving_values and serving_size:
        calculated_100g = {}
        for key, val in per_serving.items():
            if val is not None:
                calculated_100g[key] = round((val / serving_size) * 100, 2)
            else:
                calculated_100g[key] = None
        merged["nutrients_per_100g"] = calculated_100g
        merged["extraction_notes"] += " | per_100g calculated from per_serving"
    elif serving_size and has_100g_values and has_serving_values:
        merged["nutrients_per_100g"] = _validate_nutrients(
            per_100g, per_serving, serving_size
        )
    return merged


def _merge_triple_extractions(front: dict, nutrition: dict, ingredients: dict) -> dict:
    """
    Merges three separate label image extractions.
    Front provides:       product_name, brand, claims
    Nutrition provides:   nutrients_per_serving, nutrients_per_100g, serving_size
    Ingredients provides: ingredients text
    """
    merged = {
        "product_name": front.get("product_name"),
        "brand": front.get("brand"),
        "fssai_license": (
            front.get("fssai_license")
            or ingredients.get("fssai_license")
        ),
        "claims": front.get("claims", []),
        "serving_size_g": nutrition.get("serving_size_g") or front.get("serving_size_g"),
        "servings_per_pack": nutrition.get("servings_per_pack"),
        "ingredients": ingredients.get("ingredients"),
        "nutrients_per_serving": nutrition.get("nutrients_per_serving", {}),
        "nutrients_per_100g": nutrition.get("nutrients_per_100g", {}),
        "label_language": front.get("label_language", "English"),
        "extraction_notes": (
            f"Front: {front.get('extraction_notes', '')} | "
            f"Nutrition: {nutrition.get('extraction_notes', '')} | "
            f"Ingredients: {ingredients.get('extraction_notes', '')}"
        ),
        "validation_issues": [],
        "extraction_confidence": "HIGH",
        "dual_image": False,
        "triple_image": True,
    }
    serving_size = merged.get("serving_size_g")
    per_100g = merged.get("nutrients_per_100g", {})
    per_serving = merged.get("nutrients_per_serving", {})

    has_100g = any(v is not None for v in per_100g.values()) if per_100g else False
    has_serving = any(v is not None for v in per_serving.values()) if per_serving else False

    if not has_100g and has_serving and serving_size:
        # Check if per_serving values look like per_100g values
        # A biscuit serving of 15g cannot have 481 kcal — that is per_100g
        energy_per_serving = per_serving.get("energy_kcal")
        if energy_per_serving and serving_size and energy_per_serving > (serving_size * 5):
            # Values are too large to be per serving — treat as per_100g directly
            merged["nutrients_per_100g"] = per_serving
            merged["nutrients_per_serving"] = {}
        else:
            # Values look correct for per serving — calculate per_100g
            calculated = {}
            for key, val in per_serving.items():
                calculated[key] = round((val / serving_size) * 100, 2) if val is not None else None
            merged["nutrients_per_100g"] = calculated
    elif has_100g and has_serving and serving_size:
        merged["nutrients_per_100g"] = _validate_nutrients(per_100g, per_serving, serving_size)

    return merged


async def image_merger_node(state: NutriGuardState) -> dict:
    """
    Entry node — handles single, dual, and triple image inputs.

    Single image:  passes through to vision node
    Dual image:    front (claims) + back (nutrition + ingredients)
    Triple image:  front (claims) + back (nutrition) + ingredients image
    """
    start_time = time.time()

    has_front = state.get("front_image_bytes") is not None
    has_back = state.get("back_image_bytes") is not None
    has_ingredients = state.get("ingredients_image_bytes") is not None

    # ── Single image mode ──────────────────────────────────────
    if not has_front and not has_back:
        logger.info("image_merger.single_image_mode")
        return {}

    # ── Triple image mode ──────────────────────────────────────
    if has_front and has_back and has_ingredients:
        logger.info("image_merger.triple_image_mode")

        front_data = _extract_from_image(
            state["front_image_bytes"],
            FRONT_PROMPT,
            "front"
        )
        logger.info(
            "image_merger.front_extracted",
            product=front_data.get("product_name"),
            claims=len(front_data.get("claims", [])),
        )

        nutrition_data = _extract_with_consensus(
            state["back_image_bytes"],
            NUTRITION_ONLY_PROMPT,
            "nutrition",
            runs=5,
        )
        logger.info(
            "image_merger.nutrition_extracted",
            serving_size=nutrition_data.get("serving_size_g"),
            has_energy=bool(
                nutrition_data.get("nutrients_per_100g", {}).get("energy_kcal")
                or nutrition_data.get("nutrients_per_serving", {}).get("energy_kcal")
            ),
        )

        ingredients_data = _extract_from_image(
            state["ingredients_image_bytes"],
            INGREDIENTS_ONLY_PROMPT,
            "ingredients"
        )
        logger.info(
            "image_merger.ingredients_extracted",
            has_ingredients=bool(ingredients_data.get("ingredients")),
        )

        merged = _merge_triple_extractions(front_data, nutrition_data, ingredients_data)
        elapsed_ms = round((time.time() - start_time) * 1000)

        logger.info(
            "image_merger.triple_merge_complete",
            product=merged.get("product_name"),
            claims=len(merged.get("claims", [])),
            has_ingredients=bool(merged.get("ingredients")),
            elapsed_ms=elapsed_ms,
        )

        return {"extraction_result": merged}

    # ── Dual image mode ────────────────────────────────────────
    if has_front and has_back:
        logger.info("image_merger.dual_image_mode")

        front_data = _extract_from_image(
            state["front_image_bytes"],
            FRONT_PROMPT,
            "front"
        )
        logger.info(
            "image_merger.front_extracted",
            product=front_data.get("product_name"),
            claims=len(front_data.get("claims", [])),
        )

        back_data = _extract_with_consensus(
            state["back_image_bytes"],
            BACK_PROMPT,
            "back",
            runs=5,
        )
        logger.info(
            "image_merger.back_extracted",
            serving_size=back_data.get("serving_size_g"),
            has_ingredients=bool(back_data.get("ingredients")),
        )

        merged = _merge_extractions(front_data, back_data)
        elapsed_ms = round((time.time() - start_time) * 1000)

        logger.info(
            "image_merger.merge_complete",
            product=merged.get("product_name"),
            claims=len(merged.get("claims", [])),
            elapsed_ms=elapsed_ms,
        )

        return {"extraction_result": merged}

    # ── Front only ─────────────────────────────────────────────
    if has_front and not has_back:
        logger.warning("image_merger.front_only — no nutrition data available")
        front_data = _extract_from_image(
            state["front_image_bytes"],
            FRONT_PROMPT,
            "front"
        )
        front_data["validation_issues"] = ["No back label provided — nutrition data unavailable"]
        front_data["extraction_confidence"] = "LOW"
        front_data["dual_image"] = False
        front_data["triple_image"] = False
        return {"extraction_result": front_data}

    return {}