"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


# ===== Request Models =====

class CreateCollectionRequest(BaseModel):
    """Request model for creating a new collection"""
    name: Optional[str] = None
    description: Optional[str] = None


class StartRunRequest(BaseModel):
    """Request model for starting a run"""
    model_id: int = Field(..., description="ID of the model to use")
    threshold: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence threshold (0.0 to 1.0)"
    )


# ===== Response Models =====

class CollectionResponse(BaseModel):
    """Response model for collection operations"""
    model_config = ConfigDict(from_attributes=True)
    
    collection_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: str
    updated_at: str
    image_count: int = 0
    live_mussel_count: int = 0


class CollectionListResponse(BaseModel):
    """Simplified collection info for list view"""
    model_config = ConfigDict(from_attributes=True)
    
    collection_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: str
    image_count: int = 0
    live_mussel_count: int = 0


class ModelResponse(BaseModel):
    """Response model for model information"""
    model_config = ConfigDict(from_attributes=True)
    
    model_id: int
    name: str
    type: str
    weights_path: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class RunResponse(BaseModel):
    """Response model for run operations"""
    model_config = ConfigDict(from_attributes=True)
    
    run_id: int
    collection_id: int
    model_id: int
    threshold: float
    status: str
    started_at: str
    finished_at: Optional[str] = None
    error_msg: Optional[str] = None
    total_images: int = 0
    processed_count: int = 0
    live_mussel_count: int = 0


class ImageResponse(BaseModel):
    """Response model for image information"""
    model_config = ConfigDict(from_attributes=True)
    
    image_id: int
    filename: str
    stored_path: str
    file_hash: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: str
    updated_at: str
    processed_model_ids: List[int] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response model for image upload operations"""
    collection_id: int
    image_ids: List[int]
    count: int
    added_count: int
    duplicate_count: int
    duplicate_image_ids: List[int]

