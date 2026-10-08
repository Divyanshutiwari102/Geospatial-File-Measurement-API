from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.uploaded_file import ProcessingStatus


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    feature_count: Optional[int] = None
    crs: Optional[str] = None
    status: ProcessingStatus
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileInfo(BaseModel):
    id: str
    filename: str
    feature_count: Optional[int] = None
    crs: Optional[str] = None
    status: ProcessingStatus
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
