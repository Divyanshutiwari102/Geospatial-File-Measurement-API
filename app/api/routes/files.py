import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.feature import Feature
from app.models.uploaded_file import ProcessingStatus, UploadedFile
from app.schemas.file import FileInfo, FileUploadResponse
from app.schemas.measurement import (
    FeatureMeasurement,
    MeasurementResponse,
    MeasurementSummary,
)
from app.services.file_service import process_uploaded_file, save_upload_file

router = APIRouter()


@router.post("/", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a geospatial file (.zip containing a Shapefile, or .kml) for processing.
    """
    # Validate file extension
    filename = file.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    _, ext = os.path.splitext(filename.lower())
    if ext not in [".zip", ".kml", ".wkt"]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension: {ext}. Only .zip, .kml, and .wkt are allowed.",
        )

    # Validate file size (we'll read the file to check size, but we can also rely on the server's limit)
    # We'll read the file content into memory to check size, but for large files we should stream.
    # Since we have a size limit, we'll read the file up to the limit.
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {settings.max_upload_size} bytes",
        )
    # Reset the file pointer for saving
    file.file.seek(0)

    # Save the uploaded file
    try:
        saved_path, file_id = save_upload_file(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {e!s}",
        ) from None

    # Process the file (this will save to database and return the UploadedFile object)
    try:
        db_file = process_uploaded_file(
            db=db,
            file_id=file_id,
            filename=filename,
            saved_path=saved_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Clean up the saved file if processing fails?
        # We'll leave it for now, but in production we might want to clean up.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing file: {e!s}",
        ) from None

    # Return the file info
    return FileUploadResponse(
        id=db_file.id,
        filename=db_file.filename,
        feature_count=db_file.feature_count,
        crs=db_file.crs,
        status=db_file.status,
        error_message=db_file.error_message,
        created_at=db_file.created_at,
    )


@router.get("/{file_id}", response_model=FileInfo)
@router.get("/{file_id}/", response_model=FileInfo, include_in_schema=False)
def get_file_info(
    file_id: str,
    db: Session = Depends(get_db),
):
    """
    Get information about an uploaded file by its ID.
    """
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found",
        )
    return FileInfo(
        id=db_file.id,
        filename=db_file.filename,
        feature_count=db_file.feature_count,
        crs=db_file.crs,
        status=db_file.status,
        error_message=db_file.error_message,
        created_at=db_file.created_at,
    )


@router.get("/{file_id}/measurements", response_model=MeasurementResponse, include_in_schema=False)
@router.get("/{file_id}/measurements/", response_model=MeasurementResponse)
def get_file_measurements(
    file_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get measurements for the features of an uploaded file.
    Supports pagination via limit and offset.
    """
    # Check if file exists and is completed
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found",
        )
    if db_file.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File is not ready for measurement. Current status: {db_file.status.value}",
        )

    # Get all features for this file to compute totals
    all_features_query = db.query(Feature).filter(Feature.uploaded_file_id == file_id)
    total = all_features_query.count()

    # Compute totals from all features using SQL
    from sqlalchemy import func

    total_area = (
        db.query(func.sum(Feature.measurement_value))
        .filter(
            Feature.uploaded_file_id == file_id,
            Feature.measurement_type == "area",
            Feature.measurement_supported,
        )
        .scalar()
        or 0.0
    )

    total_length = (
        db.query(func.sum(Feature.measurement_value))
        .filter(
            Feature.uploaded_file_id == file_id,
            Feature.measurement_type == "length",
            Feature.measurement_supported,
        )
        .scalar()
        or 0.0
    )

    # Compute geometry type counts
    geometry_type_counts = dict(
        db.query(Feature.geometry_type, func.count(Feature.geometry_type))
        .filter(Feature.uploaded_file_id == file_id)
        .group_by(Feature.geometry_type)
        .all()
    )

    # Query features with pagination
    features_query = (
        db.query(Feature).filter(Feature.uploaded_file_id == file_id).offset(offset).limit(limit)
    )
    features = features_query.all()

    # Build the response
    feature_measurements: list[FeatureMeasurement] = []

    for feat in features:
        # Convert geometry WKT back to GeoJSON dict (we'll use shapely to loads and then mapping)
        from shapely import wkt
        from shapely.geometry import mapping

        geom = None
        if feat.geometry_wkt:
            try:
                geom = wkt.loads(feat.geometry_wkt)
            except Exception:
                geom = None
        geom_geojson = mapping(geom) if geom is not None else {}

        # Parse properties JSON
        props = {}
        if feat.properties:
            try:
                props = json.loads(feat.properties)
            except Exception:
                props = {}

        # Build measurement block
        if feat.measurement_supported:
            measurement_block = {
                "supported": True,
                "type": feat.measurement_type,
                "value": feat.measurement_value,
                "unit": feat.measurement_unit,
                "projected_crs": feat.projected_crs_used,
            }
        else:
            measurement_block = {
                "supported": False,
                "type": None,
                "value": None,
                "unit": None,
                "projected_crs": None,
                "reason": feat.measurement_reason
                or "No measurement required or unsupported geometry type",
            }

        feature_measurements.append(
            FeatureMeasurement(
                index=feat.feature_index,
                geometry_type=feat.geometry_type,
                geometry=geom_geojson,
                crs=feat.crs,
                properties=props,
                measurement=measurement_block,
            )
        )

    # Build summary
    summary = MeasurementSummary(
        total_area=total_area,
        total_area_ha=total_area / 10000.0,  # convert to hectares
        total_area_sq_km=total_area / 1_000_000.0,  # convert to square kilometers
        total_length=total_length,
        total_length_km=total_length / 1000.0,  # convert to kilometers
        geometry_type_counts=geometry_type_counts,
    )

    return MeasurementResponse(
        features=feature_measurements,
        summary=summary,
        limit=limit,
        offset=offset,
        total=total,
    )
