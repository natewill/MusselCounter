"""
Pydantic request/response schemas.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: int
    name: str
    type: str
    weights_path: str


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    model_id: int
    model_name: str
    model_type: str
    threshold: float
    created_at: str
    total_images: int = 0
    processed_count: int = 0
    live_mussel_count: int = 0
    error_msg: Optional[str] = None
    first_image_path: Optional[str] = None


class RunImageSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_image_id: int
    filename: str
    stored_path: str
    live_mussel_count: int = 0
    dead_mussel_count: int = 0
    processed_at: Optional[str] = None
    error_msg: Optional[str] = None


class RunDetailResponse(BaseModel):
    run: RunResponse
    images: List[RunImageSummaryResponse]


class RecalculateResponse(BaseModel):
    run_id: int
    threshold: float
    live_mussel_count: int
    dead_mussel_count: int
    image_count: int
    images: List[Dict[str, Any]]


class UploadRunResponse(BaseModel):
    run: RunResponse


class DetectionResponse(BaseModel):
    detection_id: int
    bbox: List[float]
    class_name: str = Field(alias="class")
    confidence: float
    manually_edited: bool


class RunImageDetailResponse(BaseModel):
    run_id: int
    run_image_id: int
    model_id: int
    model_name: str
    model_type: str
    threshold: float
    filename: str
    stored_path: str
    live_mussel_count: int
    dead_mussel_count: int
    total_mussel_count: int
    processed_at: Optional[str] = None
    error_msg: Optional[str] = None
    polygons: List[Dict[str, Any]]
    can_edit: bool


class UpdateDetectionRequest(BaseModel):
    new_class: str = Field(pattern="^(live|dead)$")
