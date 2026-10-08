import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class ProcessingStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, index=True)  # UUID as string
    filename = Column(String, nullable=False)
    feature_count = Column(Integer, nullable=True)
    crs = Column(String, nullable=True)  # EPSG code as string, e.g., "EPSG:4326"
    status = Column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.PROCESSING
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship to features
    features = relationship(
        "Feature", back_populates="uploaded_file", cascade="all, delete-orphan"
    )
