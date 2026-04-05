"""
tests/test_phase1_skeleton.py
Phase 1 skeleton verification tests.
"""

import os
import pytest

os.environ.setdefault("GEMINI_API_KEY", "test_key_placeholder")
os.environ.setdefault("APP_ENV", "testing")


def test_settings_load():
    from app.core.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.APP_VERSION == "0.1.0"
    assert settings.APP_ENV == "testing"


def test_health_endpoint_returns_200():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint_version():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.json()["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_pipeline_runs_end_to_end():
    from app.pipeline.graph import nutriguard_pipeline
    result = await nutriguard_pipeline.ainvoke({
        "image_bytes": b"fake",
        "image_filename": "test.jpg",
        "pipeline_metadata": {},
    })
    assert "final_report" in result
    assert "fraud_score" in result
    assert result["fraud_score"]["score"] >= 0


@pytest.mark.asyncio
async def test_pipeline_state_populated():
    from app.pipeline.graph import nutriguard_pipeline
    result = await nutriguard_pipeline.ainvoke({
        "image_bytes": b"fake",
        "image_filename": "test.jpg",
        "pipeline_metadata": {},
    })
    assert "extraction_result" in result
    assert "math_validation_result" in result
    assert "regulatory_result" in result
    assert "nutriscore_result" in result


@pytest.mark.asyncio
async def test_pipeline_report_structure():
    from app.pipeline.graph import nutriguard_pipeline
    result = await nutriguard_pipeline.ainvoke({
        "image_bytes": b"fake",
        "image_filename": "test.jpg",
        "pipeline_metadata": {},
    })
    report = result["final_report"]
    assert "version" in report
    assert "product" in report
    assert "fraud_assessment" in report
    assert "layer_results" in report


def test_exception_hierarchy():
    from app.core.exceptions import ExtractionError, NutriGuardError
    err = ExtractionError("test", {"detail": "blurry"})
    assert isinstance(err, NutriGuardError)
    assert err.to_dict()["error"] == "ExtractionError"