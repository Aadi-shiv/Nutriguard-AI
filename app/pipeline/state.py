"""
app/pipeline/state.py
Shared state object for the LangGraph pipeline.
"""

from __future__ import annotations
from typing import Any, TypedDict


class NutriGuardState(TypedDict, total=False):
    # Single image input
    image_bytes: bytes
    image_filename: str
    # Dual image input (front + back)
    front_image_bytes: bytes
    front_image_filename: str
    back_image_bytes: bytes
    back_image_filename: str
    ingredients_image_bytes: bytes
    ingredients_image_filename: str
    # Merged extraction (used by all downstream layers)
    extraction_result: dict[str, Any]
    math_validation_result: dict[str, Any]
    rag_result: dict[str, Any]   
    regulatory_result: dict[str, Any]
    nutriscore_result: dict[str, Any]
    ingredient_result: dict[str, Any]
    hidden_sugar_result: dict[str, Any]
    fraud_score: dict[str, Any]
    final_report: dict[str, Any]
    error: dict[str, Any] | None
    pipeline_metadata: dict[str, Any]
