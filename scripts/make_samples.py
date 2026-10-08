import os
import shutil
import tempfile
import zipfile

import geopandas as gpd
from shapely.geometry import Point


def create_sample_kml():
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample KML</name>
    <Placemark>
      <name>Sample Point</name>
      <Point>
        <coordinates>-122.0822035425683,37.42228990140251,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    os.makedirs("samples", exist_ok=True)
    with open("samples/sample.kml", "w", encoding="utf-8") as f:
        f.write(kml_content)
    print("Created samples/sample.kml")


def create_sample_shapefile():
    # Create a GeoDataFrame with one point
    gdf = gpd.GeoDataFrame(
        {"name": ["Sample Point"]},
        geometry=[Point(-122.0822035425683, 37.42228990140251)],
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
