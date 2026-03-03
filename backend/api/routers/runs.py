"""
Run-first API endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from api.schemas import (
    RecalculateResponse,
    RunDetailResponse,
    RunImageDetailResponse,
    RunImageSummaryResponse,
    RunResponse,
    UpdateDetectionRequest,
    UploadRunResponse,
)
from db import get_db
from utils.run_utils.service import (
    create_run_from_upload,
    delete_run,
    get_run,
    get_run_image_detail,
    list_run_images,
    list_runs,
    process_run,
    recalculate_run_threshold,
    update_detection_classification,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _to_run_response(run_row) -> dict:
    return {
        "run_id": run_row["run_id"],
        "model_id": run_row["model_id"],
        "model_name": run_row["model_name"],
        "model_type": run_row["model_type"],
        "threshold": float(run_row["threshold"]),
        "created_at": run_row["created_at"],
        "total_images": int(run_row["total_images"] or 0),
        "processed_count": int(run_row["processed_count"] or 0),
        "live_mussel_count": int(run_row["live_mussel_count"] or 0),
        "error_msg": run_row["error_msg"],
        "first_image_path": run_row["first_image_path"] if "first_image_path" in run_row.keys() else None,
    }


def _to_run_image_response(image_row) -> dict:
    stored_path = image_row["stored_path"]
    return {
        "run_image_id": image_row["run_image_id"],
        "filename": Path(stored_path).name,
        "stored_path": stored_path,
        "live_mussel_count": int(image_row["live_mussel_count"] or 0),
        "dead_mussel_count": int(image_row["dead_mussel_count"] or 0),
        "processed_at": image_row["processed_at"],
        "error_msg": image_row["error_msg"],
    }


@router.post("", response_model=UploadRunResponse)
async def create_run_endpoint(
    background_tasks: BackgroundTasks,
    model_id: int = Form(...),
    threshold: float = Form(0.5),
    files: List[UploadFile] | None = File(None),
):
    """
    Upload files and create a run in one call.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one image is required")

    async with get_db() as db:
        run = await create_run_from_upload(db, model_id=model_id, files=files, threshold=threshold)

    run_id = int(run["run_id"])

    async def run_task():
        await process_run(run_id, get_db)

    background_tasks.add_task(run_task)

    async with get_db() as db:
        created = await get_run(db, run_id)
        if not created:
            raise HTTPException(status_code=500, detail="Run was created but could not be loaded")
        return {"run": _to_run_response(created)}


@router.get("", response_model=List[RunResponse])
async def list_runs_endpoint() -> List[RunResponse]:
    async with get_db() as db:
        runs = await list_runs(db)
        return [RunResponse.model_validate(_to_run_response(run)) for run in runs]


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run_detail_endpoint(run_id: int) -> RunDetailResponse:
    async with get_db() as db:
        run = await get_run(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        images = await list_run_images(db, run_id)

        run_payload = RunResponse.model_validate(_to_run_response(run))
        image_payload = [
            RunImageSummaryResponse.model_validate(_to_run_image_response(row))
            for row in images
        ]
        return RunDetailResponse(run=run_payload, images=image_payload)


@router.delete("/{run_id}")
async def delete_run_endpoint(run_id: int):
    async with get_db() as db:
        await delete_run(db, run_id)
        return {"deleted": True, "run_id": run_id}


@router.get("/{run_id}/recalculate", response_model=RecalculateResponse)
async def recalculate_threshold_endpoint(run_id: int, threshold: float):
    async with get_db() as db:
        result = await recalculate_run_threshold(db, run_id, threshold)
        return RecalculateResponse.model_validate(result)


@router.get("/{run_id}/images/{run_image_id}", response_model=RunImageDetailResponse)
async def get_run_image_detail_endpoint(run_id: int, run_image_id: int):
    async with get_db() as db:
        detail = await get_run_image_detail(db, run_id, run_image_id)
        return RunImageDetailResponse.model_validate(detail)


@router.patch("/{run_id}/images/{run_image_id}/detections/{detection_id}")
async def update_detection_endpoint(
    run_id: int,
    run_image_id: int,
    detection_id: int,
    payload: UpdateDetectionRequest,
):
    async with get_db() as db:
        result = await update_detection_classification(
            db,
            run_id=run_id,
            run_image_id=run_image_id,
            detection_id=detection_id,
            new_class=payload.new_class,
        )
        return result
