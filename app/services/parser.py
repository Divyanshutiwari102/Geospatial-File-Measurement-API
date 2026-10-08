"""
Service for parsing geospatial files (KML and zipped Shapefiles).
"""

import os
import tempfile
import zipfile

import geopandas as gpd


def parse_file(file_path: str, filename: str) -> gpd.GeoDataFrame:
    """
    Parse an uploaded file and return a GeoDataFrame.

    Args:
        file_path: Path to the uploaded file on disk.
        filename: Original filename (used to determine type).

    Returns:
        GeoDataFrame containing the features.

    Raises:
        ValueError: If the file type is unsupported or the file is corrupt.
    """
    _, ext = os.path.splitext(filename.lower())
    if ext == ".kml":
        return _parse_kml(file_path)
    elif ext == ".zip":
        return _parse_zip_shapefile(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def _parse_kml(file_path: str) -> gpd.GeoDataFrame:
    """Parse a KML file."""
    try:
        gdf = gpd.read_file(file_path, driver="KML")
        # KML is always in EPSG:4326
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        return gdf
    except Exception as e:
        raise ValueError(f"Invalid KML file: {e!s}")


def _parse_zip_shapefile(file_path: str) -> gpd.GeoDataFrame:
    """
    Parse a zipped Shapefile.

    Expects the zip to contain .shp, .shx, .dbf, and optionally .prj files.
    Extracts to a temporary directory and reads the shapefile.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Guard against zip-slip: ensure all extracted paths are within tmpdir
                for member in zf.namelist():
                    # Get the absolute path of the member
                    member_path = os.path.join(tmpdir, member)
                    # Ensure the member path is inside tmpdir
                    if (
                        not os.path.commonpath([tmpdir, os.path.abspath(member_path)])
                        == tmpdir
                    ):
                        raise ValueError(f"Zip-slip attempt detected: {member}")
                # Extract all members
                zf.extractall(tmpdir)

            # Find the .shp file
            shp_files = []
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.lower().endswith(".shp"):
                        shp_files.append(os.path.join(root, file))

            if not shp_files:
                raise ValueError("No .shp file found in the zip archive")
            if len(shp_files) > 1:
                # If multiple, take the first one (or could raise an error)
                # For simplicity, we take the first.
                pass

            shp_file = shp_files[0]
            try:
                gdf = gpd.read_file(shp_file)
                # If the shapefile has no CRS, we cannot assume; we'll let the caller handle it.
                return gdf
            except Exception as e:
                raise ValueError(f"Invalid Shapefile: {e!s}")
        except zipfile.BadZipFile:
            raise ValueError("Corrupt or invalid zip file")
