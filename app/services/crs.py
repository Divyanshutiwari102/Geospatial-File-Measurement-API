"""
Service for handling Coordinate Reference Systems (CRS).
"""

import math
from typing import Optional, Tuple
import pyproj
from shapely.geometry import base, Point
import geopandas as gpd


def get_source_crs(gdf: gpd.GeoDataFrame) -> str:
    """
    Get the source CRS from a GeoDataFrame as an EPSG string.

    Args:
        gdf: GeoDataFrame with a CRS.

    Returns:
        EPSG code string, e.g., "EPSG:4326".

    Raises:
        ValueError: If the CRS cannot be determined.
    """
    if gdf.crs is None:
        raise ValueError(
            "Source CRS is missing (no .prj file for Shapefile or undefined CRS)"
        )

    # Try to convert to EPSG code
    try:
        epsg_code = gdf.crs.to_epsg()
        if epsg_code is not None:
            return f"EPSG:{epsg_code}"
        else:
            # If no EPSG code, use the authority string
            authority = gdf.crs.authority
            if authority:
                return f"{authority[0]}:{authority[1]}"
            else:
                # Fallback to string representation
                return str(gdf.crs)
    except Exception:
        # Fallback to string representation
        return str(gdf.crs)


def get_utm_zone(latitude: float, longitude: float) -> Tuple[int, bool]:
    """
    Calculate the UTM zone and hemisphere for a given latitude and longitude.

    Args:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.

    Returns:
        Tuple of (zone_number, is_northern_hemisphere)
    """
    if latitude > 84 or latitude < -80:
        # Polar regions: we'll handle separately in get_projected_crs
        return (0, latitude >= 0)

    zone_number = int((longitude + 180) // 6) + 1
    is_northern = latitude >= 0
    return (zone_number, is_northern)


def get_projected_crs_for_geometry(
    gdf: gpd.GeoDataFrame, per_feature: bool = False
) -> Optional[str]:
    """
    Determine a projected CRS suitable for area/length calculations.

    If the source CRS is already projected and in meters, return it.
    If geographic (lat/lon), calculate a UTM zone based on the centroid (or per feature).
    For polar regions, use an appropriate projection (e.g., UPS or equal-area).

    Args:
        gdf: GeoDataFrame with geometries.
        per_feature: If True, return CRS per feature (not implemented here; we'll use per-file for simplicity).
                    For now, we compute a single CRS for the entire dataset.

    Returns:
        EPSG string for a projected CRS, or None if cannot determine.

    Note:
        This function returns a single CRS for the entire GeoDataFrame.
        For per-feature UTM, we would need to compute per feature, but that is more complex.
        We'll implement a simple per-file CRS selection based on centroid.
    """
    if gdf.crs is None:
        return None

    # Check if the CRS is already projected and in meters
    try:
        # pyproj.CRS has a method to check if it's projected
        if gdf.crs.is_projected:
            # Check if the units are meters
            units = gdf.crs.axis_info[0].unit_name
            if units.lower() == "metre":
                return str(gdf.crs)
    except Exception:
        pass

    # If geographic (latitude/longitude), compute UTM zone from centroid
    if gdf.crs.is_geographic:
        # Ensure we are in lon/lat (EPSG:4326) for centroid calculation
        if gdf.crs.to_epsg() != 4326:
            # Reproject to 4326 for centroid calculation
            gdf_4326 = gdf.to_crs("EPSG:4326")
        else:
            gdf_4326 = gdf

        # Compute centroid of the entire dataset
        centroid = gdf_4326.geometry.union_all().centroid
        lon, lat = centroid.x, centroid.y

        # Handle polar regions: use UPS or equal-area
        if lat >= 84:
            return "EPSG:32661"  # WGS 84 / UPS North
        elif lat <= -80:
            return "EPSG:32761"  # WGS 84 / UPS South
        else:
            zone_number, is_northern = get_utm_zone(lat, lon)
            if zone_number == 0:
                # This shouldn't happen because we filtered polar regions above
                zone_number = 1
            hemisphere_code = 32600 if is_northern else 32700
            epsg = hemisphere_code + zone_number
            return f"EPSG:{epsg}"

    # If we reach here, we couldn't determine a projected CRS
    return None
