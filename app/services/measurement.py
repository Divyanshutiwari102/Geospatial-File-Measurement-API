"""
Service for calculating measurements (area and length) from geometries.
"""

import numpy as np
from typing import Any, Dict, List
import pyproj
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
from shapely.validation import make_valid
from shapely import transform


def calculate_measurements(
    gdf: gpd.GeoDataFrame,
    projected_crs: str,
) -> list[dict[str, Any]]:
    """
    Calculate area or length for each feature in the GeoDataFrame.

    Args:
        gdf: GeoDataFrame with features (in any CRS).
        projected_crs: EPSG string of the projected CRS to use for measurement.

    Returns:
        List of dictionaries, each containing:
        - index: feature index in the original GeoDataFrame
        - geometry_type: string (e.g., "Polygon", "LineString")
        - supported: bool
        - measurement_type: "area" or "length" or None
        - value: float or None
        - unit: string (e.g., "square_meters", "meters") or None
        - reason: string explaining why not supported (if supported=False)
    """
    results = []

    # Create a transformer from the source CRS to the projected CRS
    source_crs = gdf.crs
    project = pyproj.Transformer.from_crs(
        source_crs, projected_crs, always_xy=True
    ).transform

    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            results.append(
                {
                    "index": int(idx),
                    "geometry_type": "None",
                    "supported": False,
                    "measurement_type": None,
                    "value": None,
                    "unit": None,
                    "reason": "Null or empty geometry",
                }
            )
            continue

        # Validate and fix invalid geometries if possible
        if not geom.is_valid:
            geom = make_valid(geom)
            if geom is None or geom.is_empty:
                results.append(
                    {
                        "index": int(idx),
                        "geometry_type": geom.geom_type if geom else "Unknown",
                        "supported": False,
                        "measurement_type": None,
                        "value": None,
                        "unit": None,
                        "reason": "Invalid geometry that could not be fixed",
                    }
                )
                continue

        geometry_type = geom.geom_type

        # Initialize result dict
        result = {
            "index": int(idx),
            "geometry_type": geometry_type,
            "supported": False,
            "measurement_type": None,
            "value": None,
            "unit": None,
            "reason": "",
        }

        # Handle GeometryCollection by iterating over its parts
        if geometry_type == "GeometryCollection":
            # For simplicity, we don't support measurement on GeometryCollection
            result["reason"] = "GeometryCollection not supported for measurement"
            results.append(result)
            continue

        # For points, no measurement is needed (supported=False with reason)
        if isinstance(geom, Point) or geom.geom_type == "Point":
            result["supported"] = False
            result["reason"] = "No measurement required for point features"
            results.append(result)
            continue

        # For Polygons and LineStrings (and their multi variants) we calculate area or length
        if geom.geom_type in ("Polygon", "MultiPolygon"):
            # Area calculation
            try:
                # Project the geometry
                projected_geom = transform(geom, project, interleaved=False)
                area = projected_geom.area  # in square meters
                result["supported"] = True
                result["measurement_type"] = "area"
                result["value"] = area
                result["unit"] = "square_meters"
                # Also compute hectares and sq km for convenience (though we return only one unit per requirement)
                # We'll stick to square_meters as per requirement, but note that we can add more later.
            except Exception as e:  # noqa: BLE001
                result["supported"] = False
                result["reason"] = f"Area calculation failed: {e!s}"
        elif geom.geom_type in ("LineString", "MultiLineString"):
            # Length calculation
            try:
                projected_geom = transform(geom, project, interleaved=False)
                length = projected_geom.length  # in meters
                result["supported"] = True
                result["measurement_type"] = "length"
                result["value"] = length
                result["unit"] = "meters"
            except Exception as e:  # noqa: BLE001
                result["supported"] = False
                result["reason"] = f"Length calculation failed: {e!s}"
        else:
            # Other geometry types (e.g., Triangle, etc.) are not supported
            result["supported"] = False
            result["reason"] = f"Unsupported geometry type: {geometry_type}"

        results.append(result)

    return results
