"""
app/pipeline/nodes/vision.py
-----------------------------
Vision extraction node — uses Groq (llama-4-scout) to extract
structured nutrition data from a food label image.
"""

import json
import time
import base64
from groq import Groq

from app.pipeline.state import NutriGuardState
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ExtractionError

logger = get_logger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

EXTRACTION_PROMPT = """You are a food label analysis expert. Analyze this Indian packaged food product label image carefully.

Extract ALL information visible on the label and return ONLY a valid JSON object.
No explanation, no markdown, no code blocks. Just raw JSON.

Return exactly this structure:

{
  "product_name": "full product name as printed",
  "brand": "brand name",
  "fssai_license": "FSSAI license number if visible, else null",
  "serving_size_g": <number in grams, null if not found>,
  "servings_per_pack": <number, null if not found>,
  "claims": ["list", "of", "all", "front", "label", "claims"],
  "ingredients": "full ingredients text if visible, else null",
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
  "extraction_notes": "any issues or uncertainties in reading the label"
}

IMPORTANT RULES:
- Use null for any value you cannot read clearly
- Never guess or estimate values
- All nutrient values must be numbers, not strings
- serving_size_g must be a number only, not 30g
- If label shows per 100g but not per serving, calculate per serving using serving_size_g
- If label shows per serving but not per 100g, calculate per 100g using serving_size_g"""


def _detect_image_type(image_bytes: bytes) -> str:
    """Detect image media type from magic bytes."""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif image_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    return "image/jpeg"


def _validate_extraction(data: dict) -> dict:
    """Validates and cleans the extracted data."""
    issues = []

    if not data.get("product_name"):
        issues.append("product_name missing")

    serving = data.get("serving_size_g")
    if serving is not None:
        if serving <= 0 or serving > 1000:
            issues.append(f"serving_size_g={serving} outside valid range")
            data["serving_size_g"] = None

    for section in ["nutrients_per_100g", "nutrients_per_serving"]:
        nutrients = data.get(section, {})
        if not nutrients:
            continue
        protein = nutrients.get("protein_g")
        if protein is not None and protein > 100:
            issues.append(f"{section}.protein_g={protein} exceeds 100g — impossible")
            nutrients["protein_g"] = None
        for key, value in nutrients.items():
            if value is not None and isinstance(value, (int, float)) and value < 0:
                issues.append(f"{section}.{key}={value} is negative — impossible")
                nutrients[key] = None

    data["validation_issues"] = issues
    data["extraction_confidence"] = (
        "HIGH" if len(issues) == 0
        else "MEDIUM" if len(issues) <= 2
        else "LOW"
    )
    return data


async def vision_extraction_node(state: NutriGuardState) -> dict:
    """
    Extracts structured nutrition data from a food label image using Groq.
    """
    logger.info("vision_extraction.start", filename=state.get("image_filename"))
    start_time = time.time()

    try:
        image_bytes = state["image_bytes"]
        media_type = _detect_image_type(image_bytes)
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        logger.info("vision_extraction.sending_to_groq", media_type=media_type)

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0, 
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}"
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info("vision_extraction.response_received", length=len(raw_text))

        # Remove markdown code blocks if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1])

        try:
            extracted_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("vision_extraction.json_parse_failed", error=str(e))
            raise ExtractionError(
                "Groq returned invalid JSON. Image may be unclear.",
                {"raw_response": raw_text[:500], "parse_error": str(e)},
            )

        validated_data = _validate_extraction(extracted_data)

        elapsed_ms = round((time.time() - start_time) * 1000)
        logger.info(
            "vision_extraction.complete",
            product=validated_data.get("product_name"),
            confidence=validated_data.get("extraction_confidence"),
            elapsed_ms=elapsed_ms,
        )

        return {"extraction_result": validated_data}

    except ExtractionError:
        raise
    except Exception as e:
        logger.exception("vision_extraction.unexpected_error", error=str(e))
        raise ExtractionError(
            f"Vision extraction failed: {str(e)}",
            {"filename": state.get("image_filename")},
        )