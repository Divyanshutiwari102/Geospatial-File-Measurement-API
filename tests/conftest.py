import os
import tempfile
import zipfile

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base
from app.main import create_app


@pytest.fixture
def test_db(monkeypatch):
    """Create a temporary SQLite database for testing."""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Override the database URL
    test_database_url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", test_database_url)

    # Get engine from the module
    from app.db.session import get_engine

    test_engine = get_engine()
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Override the app's dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # We'll return the test engine and session local so that the test can use them if needed
    yield {
        "database_url": test_database_url,
        "engine": test_engine,
        "session_local": TestingSessionLocal,
        "override_get_db": override_get_db,
        "db_path": db_path,
    }

    # Clean up
    test_engine.dispose()
    os.unlink(db_path)


@pytest.fixture
def test_upload_dir(monkeypatch):
    """Create a temporary upload directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(settings, "upload_dir", tmpdir)
        yield tmpdir


@pytest.fixture
def client(test_db, test_upload_dir):
    """Create a test client with overridden dependencies."""
    app = create_app()

    # Override the get_db dependency
    from app.db.session import get_db

    app.dependency_overrides[get_db] = test_db["override_get_db"]

    # Create a test client
    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_kml_content():
    """
    Generate a simple KML content with a point, a line string, and a polygon.
    """
    # Create a valid polygon: square from (0,0) to (0.01,0.01)
    polygon_coords = "0,0,0 0,0.01,0 0.01,0.01,0 0.01,0,0 0,0,0"
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Point</name>
      <Point>
        <coordinates>0,0,0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>LineString</name>
      <LineString>
        <coordinates>0,0,0 0,0.01,0 0.01,0.01,0 0.01,0,0</coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Polygon</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>{polygon_coords}</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    return kml.encode("utf-8")


@pytest.fixture
def sample_shapefile():
    """
    Generate a simple shapefile in memory and return the zipped bytes.
    The shapefile will be in EPSG:4326 and contain a polygon of approximately 1km x 1km near the equator.
    """
    # Create a square of 0.009 degrees by 0.009 degrees (approx 1km x 1km at the equator)
    poly = Polygon([(0, 0), (0, 0.009), (0.009, 0.009), (0.009, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"id": [1], "geometry": [poly]}, crs="EPSG:4326")

    # Create a temporary directory and save the shapefile
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "test.shp")
        gdf.to_file(shp_path)

        # Now zip the shapefile components
        zip_path = os.path.join(tmpdir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in os.listdir(tmpdir):
                if file.endswith((".shp", ".shx", ".dbf", ".prj")):
                    zipf.write(os.path.join(tmpdir, file), file)

        # Read the zip bytes
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

    return zip_bytes
