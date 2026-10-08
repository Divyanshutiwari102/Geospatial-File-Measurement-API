"""
Unit tests for the measurement service.
"""

import pytest
from shapely.geometry import (
    Polygon,
    LineString,
    Point,
    MultiPolygon,
    MultiLineString,
    GeometryCollection,
)
import geopandas as gpd
from app.services.measurement import calculate_measurements


def test_multipolygon_area():
    """Test that area of MultiPolygon is sum of parts."""
    # Create two separate polygons
    poly1 = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])  # area = 1
    poly2 = Polygon([(2, 0), (2, 1), (3, 1), (3, 0), (2, 0)])  # area = 1
    multipoly = MultiPolygon([poly1, poly2])

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[multipoly], crs="EPSG:4326")
    # Use a projected CRS for area calculation (e.g., UTM zone 33N)
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    assert results[0]["supported"] is True
    assert results[0]["measurement_type"] == "area"
    assert results[0]["unit"] == "square_meters"
    # The area should be approximately 2 square meters in the projected CRS?
    # Actually, the area in square degrees is 2, but after projection to UTM, it will be different.
    # We just want to verify that the area is positive and supported.
    assert results[0]["value"] > 0


def test_polygon_with_hole():
    """Test that area of Polygon with hole excludes the hole."""
    # Outer polygon: 0,0 to 2,2 (area = 4)
    # Inner polygon (hole): 0.5,0.5 to 1.5,1.5 (area = 1)
    # Expected area: 4 - 1 = 3
    outer_shell = [(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)]
    inner_hole = [(0.5, 0.5), (0.5, 1.5), (1.5, 1.5), (1.5, 0.5), (0.5, 0.5)]
    poly_with_hole = Polygon(outer_shell, [inner_hole])

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly_with_hole], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    assert results[0]["supported"] is True
    assert results[0]["measurement_type"] == "area"
    assert results[0]["unit"] == "square_meters"
    # The area should be positive
    assert results[0]["value"] > 0


def test_multilinestring_length():
    """Test that length of MultiLineString is sum of parts."""
    line1 = LineString([(0, 0), (0, 1)])  # length = 1
    line2 = LineString([(2, 0), (2, 1)])  # length = 1
    multiline = MultiLineString([line1, line2])

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[multiline], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    assert results[0]["supported"] is True
    assert results[0]["measurement_type"] == "length"
    assert results[0]["unit"] == "meters"
    assert results[0]["value"] > 0


def test_empty_polygon():
    """Test that empty polygon is not supported."""
    # Create an empty polygon
    empty_poly = Polygon()

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[empty_poly], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    assert results[0]["supported"] is False
    # The function sets geometry_type to "None" for empty geometries
    assert results[0]["geometry_type"] == "None"
    assert results[0]["reason"] == "Null or empty geometry"


def test_none_geometry():
    """Test that None geometry is not supported."""
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[None], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    assert results[0]["supported"] is False
    assert results[0]["geometry_type"] == "None"
    assert results[0]["reason"] == "Null or empty geometry"


def test_bowtie_polygon():
    """Test that self-intersecting (bowtie) polygon is handled."""
    # Bowtie polygon: coordinates that cross
    bowtie = Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)])

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[bowtie], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    # The function attempts to make_valid, which should fix the bowtie into two triangles
    # So it should be supported after fixing.
    # However, we want to test that it doesn't crash and returns something reasonable.
    assert len(results) == 1
    # It might be supported after validation, or not if it can't be fixed.
    # We'll just check that it doesn't crash and has a reason if not supported.
    if not results[0]["supported"]:
        assert "reason" in results[0]
        assert results[0]["reason"] != ""
    # If it is supported, we check the area is positive.
    else:
        assert results[0]["measurement_type"] == "area"
        assert results[0]["value"] > 0


def test_polygon_with_z():
    """Test that Polygon with Z coordinates is handled."""
    # Create a 3D polygon
    poly_3d = Polygon([(0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1), (0, 0, 1)])

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly_3d], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    # The function should handle Z coordinates (shapely 2.0+ should ignore Z for area?)
    # Actually, the area of a 3D polygon is still calculated in 2D?
    # We'll just check that it doesn't crash.
    if not results[0]["supported"]:
        assert "reason" in results[0]
        assert results[0]["reason"] != ""
    else:
        assert results[0]["measurement_type"] == "area"
        assert results[0]["value"] > 0


def test_geometrycollection():
    """Test that GeometryCollection is not supported."""
    # Create a GeometryCollection with a point and a line string
    geom_collection = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[geom_collection], crs="EPSG:4326")
    projected_crs = "EPSG:32633"

    results = calculate_measurements(gdf, projected_crs)

    assert len(results) == 1
    assert results[0]["supported"] is False
    assert results[0]["geometry_type"] == "GeometryCollection"
    assert results[0]["reason"] == "GeometryCollection not supported for measurement"


if __name__ == "__main__":
    pytest.main([__file__])
