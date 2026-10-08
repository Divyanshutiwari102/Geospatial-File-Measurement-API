"""
Service for handling file uploads and processing.
"""

import json
import os
import shutil
import uuid

import numpy as np
import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.feature import Feature
from app.models.uploaded_file import ProcessingStatus, UploadedFile
from app.services.crs import get_projected_crs_for_geometry, get_source_crs
from app.services.measurement import calculate_measurements
from app.services.parser import parse_file


def save_upload_file(upload_file: UploadFile) -> tuple[str, str]:
    """
    Save the uploaded file to the upload directory and return the saved file path and a unique ID.

    Args:
        upload_file: The uploaded file from FastAPI.

    Returns:
        Tuple of (saved_file_path, file_id)
    """
    # Generate a unique filename
    file_id = str(uuid.uuid4())
    # Preserve the original extension
    _, ext = os.path.splitext(upload_file.filename)
    if not ext:
        ext = ".dat"  # fallback
    saved_filename = f"{file_id}{ext}"
    saved_path = os.path.join(settings.upload_dir, saved_filename)

    # Ensure the upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Save the file
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return saved_path, file_id


def process_uploaded_file(
    db: Session,
    file_id: str,
    filename: str,
    saved_path: str,
) -> UploadedFile:
    """
    Process an uploaded file: parse, determine CRS, calculate measurements, and save to database.

    Args:
        db: Database session.
        file_id: Unique ID for the file.
        filename: Original filename.
        saved_path: Path to the saved uploaded file.

    Returns:
        UploadedFile ORM object with the results.
    """
    # Create an initial UploadedFile record with status PROCESSING
    db_file = UploadedFile(
        id=file_id,
        filename=filename,
        status=ProcessingStatus.PROCESSING,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    try:
        # Step 1: Parse the file into a GeoDataFrame
        gdf = parse_file(saved_path, filename)

        # Step 2: Get the source CRS
        try:
            source_crs_str = get_source_crs(gdf)
        except ValueError as e:
            raise ValueError(f"CRS error: {e!s}")

        # Step 3: Determine projected CRS for measurement
        projected_crs = get_projected_crs_for_geometry(gdf)
        if projected_crs is None:
            # Fallback: if we cannot determine a projected CRS, we cannot measure
            # We'll still save the file but mark as failed for measurement?
            # According to requirements, we should return a clear error if CRS missing for Shapefile.
            # For KML, we know it's EPSG:4326, so we should be able to get a projected CRS.
            # If we get here, something went wrong.
            raise ValueError(
                "Could not determine a suitable projected CRS for measurement"
            )

        # Step 4: Calculate measurements
        measurements = calculate_measurements(gdf, projected_crs)

        # Step 5: Prepare features for saving
        features_to_save = []
        total_area = 0.0
        total_length = 0.0
        geometry_type_counts = {}

        for m in measurements:
            idx = m["index"]
            row = gdf.iloc[idx]
            geom = row.geometry

            # Convert properties to JSON-serializable dict
            # We'll drop the geometry column and convert the rest to dict, then handle non-serializable types
            props = row.drop(labels="geometry").to_dict()
            # Convert numpy types, NaN, NaT, and other non-serializable types to None or string
            props_json_safe = {}
            for k, v in props.items():
                if isinstance(v, (np.integer, np.int64, np.int32)):
                    props_json_safe[k] = int(v)
                elif isinstance(v, (np.floating, np.float64, np.float32)):
                    if np.isnan(v) or np.isinf(v):
                        props_json_safe[k] = None
                    else:
                        props_json_safe[k] = float(v)
                elif isinstance(v, np.bool_):
                    props_json_safe[k] = bool(v)
                elif isinstance(v, np.ndarray):
                    props_json_safe[k] = v.tolist()
                elif pd.isna(v):  # Handles NaN, NaT, None
                    props_json_safe[k] = None
                else:
                    props_json_safe[k] = v

            # Determine measurement block
            if m["supported"]:
                measurement_block = {
                    "supported": True,
                    "type": m["measurement_type"],
                    "value": m["value"],
                    "unit": m["unit"],
                    "projected_crs": projected_crs,
                }
                # Accumulate totals
                if m["measurement_type"] == "area":
                    total_area += m["value"]
                elif m["measurement_type"] == "length":
                    total_length += m["value"]
            else:
                measurement_block = {
                    "supported": False,
                    "type": None,
                    "value": None,
                    "unit": None,
                    "projected_crs": None,
                    "reason": m["reason"],
                }

            # Count geometry types
            geom_type = m["geometry_type"]
            geometry_type_counts[geom_type] = geometry_type_counts.get(geom_type, 0) + 1

            # Create Feature ORM object
            feature = Feature(
                uploaded_file_id=file_id,
                feature_index=idx,
                geometry_type=geom_type,
                geometry_wkt=geom.wkt if geom is not None else None,
                properties=json.dumps(props_json_safe),
                crs=source_crs_str,
                measurement_supported=1 if measurement_block["supported"] else 0,
                measurement_type=measurement_block["type"],
                measurement_value=measurement_block["value"],
                measurement_unit=measurement_block["unit"],
                projected_crs_used=measurement_block["projected_crs"],
                measurement_reason=None
                if measurement_block["supported"]
                else measurement_block["reason"],
            )
            features_to_save.append(feature)

        # Step 6: Update the UploadedFile record with results
        db_file.feature_count = len(gdf)
        db_file.crs = source_crs_str
        db_file.status = ProcessingStatus.COMPLETED
        # Note: We don't save error_message here because it's successful

        # Step 7: Save features
        db.add_all(features_to_save)
        db.commit()

        # Step 8: Refresh the file object to get the features relationship (if needed)
        db.refresh(db_file)

        return db_file

    except Exception as e:
        # If any error occurs, mark the file as FAILED and save the error message
        db_file.status = ProcessingStatus.FAILED
        db_file.error_message = str(e)
        db.commit()
        db.refresh(db_file)
        # Re-raise the exception to be handled by the API layer
        raise
