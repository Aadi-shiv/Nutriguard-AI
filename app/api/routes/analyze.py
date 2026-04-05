"""
app/api/routes/analyze.py
Primary analysis endpoint for NutriGuard AI.
"""

import time
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.exceptions import ExtractionError, PipelineError
from app.core.logging import get_logger
from app.pipeline.graph import nutriguard_pipeline
from app.pipeline.state import NutriGuardState

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/analyze", response_class=JSONResponse)
async def analyze_label(
    image: Annotated[UploadFile, File(description="Food label image")],
) -> JSONResponse:
    start_time = time.time()

    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {image.content_type}",
        )

    image_bytes = await image.read()

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image too large. Maximum 10MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    logger.info("analyze.request_received", filename=image.filename)

    try:
        initial_state: NutriGuardState = {
            "image_bytes": image_bytes,
            "image_filename": image.filename or "unknown.jpg",
            "pipeline_metadata": {
                "request_start_time": start_time,
                "image_size_bytes": len(image_bytes),
            },
        }

        result = await nutriguard_pipeline.ainvoke(initial_state)
        elapsed_ms = round((time.time() - start_time) * 1000)

        if result.get("error"):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "error": result["error"],
                    "elapsed_ms": elapsed_ms,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "elapsed_ms": elapsed_ms,
                "report": result.get("final_report"),
            },
        )

    except (ExtractionError, PipelineError) as e:
        raise HTTPException(status_code=422, detail=e.to_dict())
    except Exception as e:
        logger.exception("analyze.unexpected_error", error=str(e))
        raise HTTPException(status_code=500, detail="Unexpected error occurred.")
    