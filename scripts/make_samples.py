import os
import shutil
import tempfile
import zipfile

import geopandas as gpd
from shapely.geometry import Point


def create_sample_kml():
    # Using coordinates near Statue of Liberty, New York
    center_lon = -74.0445
    center_lat = 40.6892
    # 0.0045 degrees approx 0.5km (since 0.01 degrees ~ 1.1km)
    half_size = 0.0045

    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample KML</name>
    <Placemark>
      <name>Sample Point</name>
      <Point>
        <coordinates>{center_lon},{center_lat},0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Sample LineString</name>
      <LineString>
        <coordinates>
          {center_lon - half_size},{center_lat - half_size},0
          {center_lon + half_size},{center_lat + half_size},0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Sample Polygon</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              {center_lon - half_size},{center_lat - half_size},0
              {center_lon - half_size},{center_lat + half_size},0
              {center_lon + half_size},{center_lat + half_size},0
              {center_lon + half_size},{center_lat - half_size},0
              {center_lon - half_size},{center_lat - half_size},0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    os.makedirs("samples", exist_ok=True)
    with open("samples/sample.kml", "w", encoding="utf-8") as f:
        f.write(kml_content)
    print("Created samples/sample.kml")


def create_sample_shapefile():
    # Using coordinates near Statue of Liberty, New York
    center_lon = -74.0445
    center_lat = 40.6892
    # 0.0045 degrees approx 0.5km (since 0.01 degrees ~ 1.1km)
    half_size = 0.0045
    # Offset for second polygon
    offset = 0.009

    # Create two polygons
    from shapely.geometry import Polygon

    polygon1 = Polygon([
        (center_lon - half_size, center_lat - half_size),
        (center_lon - half_size, center_lat + half_size),
        (center_lon + half_size, center_lat + half_size),
        (center_lon + half_size, center_lat - half_size),
        (center_lon - half_size, center_lat - half_size)
    ])
    polygon2 = Polygon([
        (center_lon - half_size + offset, center_lat - half_size + offset),
        (center_lon - half_size + offset, center_lat + half_size + offset),
        (center_lon + half_size + offset, center_lat + half_size + offset),
        (center_lon + half_size + offset, center_lat - half_size + offset),
        (center_lon - half_size + offset, center_lat - half_size + offset)
    ])

    gdf = gpd.GeoDataFrame(
        {"id": [1, 2], "name": ["Polygon 1", "Polygon 2"]},
        geometry=[polygon1, polygon2],
        crs="EPSG:4326",
    )

    # Create a temporary directory for the shapefile
    temp_dir = tempfile.mkdtemp()
    try:
        # Save the GeoDataFrame as a shapefile
        shp_path = os.path.join(temp_dir, "sample.shp")
        gdf.to_file(shp_path)

        # Create the zip file
        os.makedirs("samples", exist_ok=True)
        zip_path = "samples/sample_shapefile.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add all the shapefile components
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    zipf.write(file_path, file)
        print(f"Created {zip_path}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    create_sample_kml()
    create_sample_shapefile()
