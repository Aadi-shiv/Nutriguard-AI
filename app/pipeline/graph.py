"""
app/pipeline/graph.py
LangGraph orchestration for NutriGuard AI.
"""

import time
from typing import Literal

from langgraph import graph
from langgraph.graph import StateGraph, START, END

from app.pipeline.state import NutriGuardState
from app.pipeline.nodes.vision import vision_extraction_node
from app.pipeline.nodes.math_validator import math_validator_node
from app.pipeline.nodes.regulatory import regulatory_engine_node
from app.pipeline.nodes.nutriscore import nutriscore_engine_node
from app.pipeline.nodes.ingredient_parser import ingredient_parser_node
from app.pipeline.nodes.image_merger import image_merger_node
from app.core.logging import get_logger
from app.pipeline.nodes.rag_engine import rag_engine_node
from app.pipeline.nodes.hidden_sugar_detector import hidden_sugar_detector_node

logger = get_logger(__name__)


def route_after_merger(state: NutriGuardState) -> Literal["vision_extraction", "math_validator"]:
    """
    If merger already populated extraction_result (dual image),
    skip vision extraction and go straight to math validator.
    """
    if state.get("extraction_result"):
        return "math_validator"
    return "vision_extraction"


def route_on_error(state: NutriGuardState) -> Literal["continue", "end_with_error"]:
    if state.get("error"):
        return "end_with_error"
    return "continue"



async def report_aggregator_node(state: NutriGuardState) -> dict:
    logger.info("report_aggregator.start")

    extraction = state.get("extraction_result", {})
    math_val = state.get("math_validation_result", {})
    regulatory = state.get("regulatory_result", {})
    nutriscore = state.get("nutriscore_result", {})
    ingredient = state.get("ingredient_result", {})
    hidden_sugar = state.get("hidden_sugar_result", {})
    rag_result = state.get("rag_result", {})
    metadata = state.get("pipeline_metadata", {})

    fraud_signals = []
    fraud_points = 0

    # Math violations
    math_failures = math_val.get("failures", [])
    if math_failures:
        points = min(40, len(math_failures) * 15)
        fraud_points += points
        fraud_signals.append({
            "source": "math_validator",
            "signal": f"{len(math_failures)} arithmetic inconsistencies detected",
            "points": points,
        })

    # Regulatory violations
    violations = [
        v for v in regulatory.get("claim_verdicts", [])
        if v.get("verdict") == "NON_COMPLIANT"
    ]
    if violations:
        points = min(35, len(violations) * 12)
        fraud_points += points
        fraud_signals.append({
            "source": "regulatory_engine",
            "signal": f"{len(violations)} non-compliant claims found",
            "points": points,
            "details": [v["reason"] for v in violations],
        })
    # RAG violations
    rag_result = state.get("rag_result", {})
    rag_verdicts = rag_result.get("rag_verdicts", [])
    rag_violations = [v for v in rag_verdicts if v.get("verdict") == "NON_COMPLIANT"]
    if rag_violations:
        points = min(35, len(rag_violations) * 15)
        fraud_points += points
        fraud_signals.append({
            "source": "rag_engine",
            "signal": f"{len(rag_violations)} additional violations found via FSSAI regulation database",
            "points": points,
            "details": [v.get("reason", "") for v in rag_violations],
        })    

    # NutriScore health halo
    grade = nutriscore.get("grade")
    health_claims = [
        c for c in extraction.get("claims", [])
        if any(kw in c.lower() for kw in [
            "healthy", "nutritious", "guilt free", "guilt-free",
            "heart", "good for you", "clean"
        ])
    ]
    if grade in ("D", "E") and health_claims:
        fraud_points += 25
        fraud_signals.append({
            "source": "nutriscore",
            "signal": f"NutriScore {grade} product makes health claims: {health_claims}",
            "points": 25,
        })

    # Ingredient violations
    ingredient_violations = ingredient.get("violations", [])
    critical_violations = [v for v in ingredient_violations if v.get("severity") == "CRITICAL"]
    high_violations = [v for v in ingredient_violations if v.get("severity") == "HIGH"]

    if critical_violations:
        points = min(35, len(critical_violations) * 20)
        fraud_points += points
        fraud_signals.append({
            "source": "ingredient_parser",
            "signal": f"{len(critical_violations)} critical claim-ingredient contradictions",
            "points": points,
        })
    if high_violations:
        points = min(20, len(high_violations) * 10)
        fraud_points += points
        fraud_signals.append({
            "source": "ingredient_parser",
            "signal": f"{len(high_violations)} high-concern ingredient violations",
            "points": points,
        })
    # Hidden sugar violations
    hidden_sugar = state.get("hidden_sugar_result", {})
    sugar_violations = hidden_sugar.get("violations", [])
    sugar_splitting = hidden_sugar.get("sugar_splitting", {})

    critical_sugar = [v for v in sugar_violations if v.get("severity") == "CRITICAL"]
    high_sugar = [v for v in sugar_violations if v.get("severity") == "HIGH"]

    if critical_sugar:
        points = min(30, len(critical_sugar) * 20)
        fraud_points += points
        fraud_signals.append({
            "source": "hidden_sugar_detector",
            "signal": f"{len(critical_sugar)} critical hidden sugar violations",
            "points": points,
            "details": [v["message"] for v in critical_sugar],
        })

    if high_sugar:
        points = min(20, len(high_sugar) * 10)
        fraud_points += points
        fraud_signals.append({
            "source": "hidden_sugar_detector",
            "signal": f"{len(high_sugar)} hidden sugar violations detected",
            "points": points,
            "details": [v["message"] for v in high_sugar],
        })

    if sugar_splitting.get("detected") and sugar_splitting.get("count", 0) >= 3:
        fraud_points += 15
        fraud_signals.append({
            "source": "hidden_sugar_detector",
            "signal": f"Sugar splitting: {sugar_splitting['count']} sugar aliases detected",
            "points": 15,
            "details": [sugar_splitting.get("message", "")],
        })
    # High concern additives — informational
    high_concern_additives = ingredient.get("additives", {}).get("high_concern", [])
    if high_concern_additives:
        fraud_signals.append({
            "source": "ingredient_parser",
            "signal": f"{len(high_concern_additives)} high-concern additives: "
                      f"{', '.join(a['code'] for a in high_concern_additives)}",
            "points": 0,
        })

    fraud_score = min(100, max(0, fraud_points))

    def fraud_level(score):
        if score >= 70: return "HIGH"
        elif score >= 40: return "MEDIUM"
        elif score >= 15: return "LOW"
        return "MINIMAL"

    def fraud_interpretation(score):
        if score >= 70:
            return "Strong indicators of label fraud. Avoid purchase."
        elif score >= 40:
            return "Concerning discrepancies detected. Verify claims carefully."
        elif score >= 15:
            return "Minor inconsistencies detected. Broadly compliant."
        return "No significant fraud indicators detected."

    fraud_score_result = {
        "score": fraud_score,
        "level": fraud_level(fraud_score),
        "signals": fraud_signals,
        "interpretation": fraud_interpretation(fraud_score),
    }

    final_report = {
        "version": "1.0",
        "product": {
            "name": extraction.get("product_name", "Unknown"),
            "brand": extraction.get("brand", "Unknown"),
            "fssai_license": extraction.get("fssai_license"),
            "serving_size_g": extraction.get("serving_size_g"),
            "dual_image_analysis": extraction.get("dual_image", False),
        },
        "fraud_assessment": fraud_score_result,
        "layer_results": {
            "math_validation": math_val,
            "regulatory_compliance": regulatory,
            "rag_compliance": rag_result,
            "nutriscore": nutriscore,
            "ingredient_analysis": ingredient,
            "hidden_sugar": hidden_sugar,
        },
        "metadata": metadata,
    }

    metadata["report_generated_at"] = time.time()
    logger.info("report_aggregator.complete", fraud_score=fraud_score)

    return {
        "fraud_score": fraud_score_result,
        "final_report": final_report,
        "pipeline_metadata": metadata,
    }


def build_pipeline() -> StateGraph:
    graph = StateGraph(NutriGuardState)

    graph.add_node("image_merger", image_merger_node)
    graph.add_node("vision_extraction", vision_extraction_node)
    graph.add_node("math_validator", math_validator_node)
    graph.add_node("regulatory_engine", regulatory_engine_node)
    graph.add_node("rag_engine", rag_engine_node)
    graph.add_node("hidden_sugar_detector", hidden_sugar_detector_node)
    graph.add_node("nutriscore_engine", nutriscore_engine_node)
    graph.add_node("ingredient_parser", ingredient_parser_node)
    graph.add_node("report_aggregator", report_aggregator_node)

    graph.add_edge(START, "image_merger")

    graph.add_conditional_edges(
        "image_merger",
        route_after_merger,
        {
            "vision_extraction": "vision_extraction",
            "math_validator": "math_validator",
        },
    )

    graph.add_conditional_edges(
        "vision_extraction",
        route_on_error,
        {"continue": "math_validator", "end_with_error": END},
    )
    graph.add_conditional_edges(
        "math_validator",
        route_on_error,
        {"continue": "regulatory_engine", "end_with_error": END},
    )
    graph.add_conditional_edges(
        "regulatory_engine",
        route_on_error,
        {"continue": "rag_engine", "end_with_error": END},
    )
    graph.add_conditional_edges(
        "rag_engine",
        route_on_error,
        {"continue": "nutriscore_engine", "end_with_error": END},
    )
    
    graph.add_conditional_edges(
        "nutriscore_engine",
        route_on_error,
        {"continue": "ingredient_parser", "end_with_error": END},
    )
    graph.add_conditional_edges(
    "ingredient_parser",
    route_on_error,
    {"continue": "hidden_sugar_detector", "end_with_error": END},
    )
    graph.add_conditional_edges(
    "hidden_sugar_detector",
    route_on_error,
    {"continue": "report_aggregator", "end_with_error": END},
    )
    
    graph.add_edge("report_aggregator", END)

    return graph.compile()


nutriguard_pipeline = build_pipeline()