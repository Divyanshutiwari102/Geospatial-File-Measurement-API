from datetime import datetime

from pydantic import BaseModel

from app.models.uploaded_file import ProcessingStatus


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    feature_count: int | None = None
    crs: str | None = None
    status: ProcessingStatus
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileInfo(BaseModel):
    id: str
    filename: str
    feature_count: int | None = None
    crs: str | None = None
    status: ProcessingStatus
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
