
from pydantic import BaseModel, Field


class MeasurementBlock(BaseModel):
    supported: bool
    type: str | None = None  # "area" or "length"
    value: float | None = None
    unit: str | None = None
    projected_crs: str | None = None
    reason: str | None = None  # explanation when not supported

    class Config:
        # Allow population by field name or alias
        # We'll use alias for the nested structure if needed, but for now keep simple
        pass


class FeatureMeasurement(BaseModel):
    index: int
    geometry_type: str
    geometry: dict  # GeoJSON representation
    crs: str
    properties: dict  # JSON-safe properties
    measurement: MeasurementBlock


class MeasurementSummary(BaseModel):
    total_area: float = 0.0
    total_area_ha: float = 0.0  # hectares
    total_area_sq_km: float = 0.0
    total_length: float = 0.0
    total_length_km: float = 0.0
    geometry_type_counts: dict = Field(default_factory=dict)


class MeasurementResponse(BaseModel):
    features: list[FeatureMeasurement]
    summary: MeasurementSummary
    limit: int
    offset: int
    total: int

    class Config:
        from_attributes = True
