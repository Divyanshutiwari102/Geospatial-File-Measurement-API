from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    uploaded_file_id = Column(String, ForeignKey("uploaded_files.id"), nullable=False)
    feature_index = Column(Integer, nullable=False)  # index within the file
    geometry_type = Column(String, nullable=False)  # e.g., Point, LineString, Polygon
    geometry_wkt = Column(
        Text, nullable=False
    )  # Store as WKT for simplicity, could also be GeoJSON
    properties = Column(Text, nullable=True)  # JSON string of properties
    crs = Column(
        String, nullable=False
    )  # Original CRS of the feature (same as file's CRS)
    measurement_supported = Column(Integer, nullable=False)  # 0 or 1 (boolean)
    measurement_type = Column(String, nullable=True)  # "area" or "length"
    measurement_value = Column(Float, nullable=True)  # in square meters or meters
    measurement_unit = Column(String, nullable=True)  # e.g., "square_meters", "meters"
    projected_crs_used = Column(
        String, nullable=True
    )  # CRS used for measurement, e.g., "EPSG:32633"
    measurement_reason = Column(
        Text, nullable=True
    )  # Reason if measurement is not supported
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship to uploaded file
    uploaded_file = relationship("UploadedFile", back_populates="features")
