# Geospatial File Measurement API

A production-quality backend service for uploading geospatial files (Shapefile in ZIP format or KML) and extracting measurements (area for polygons, length for lines) from every feature.

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
- [API](#api)
- [Architecture](#architecture)
- [Design Decisions](#design-decisions)
- [Learnings](#learnings)
- [Future Scope](#future-scope)

## Overview

This service accepts a geospatial file (a .zip containing a Shapefile, or a .kml, or a .wkt), extracts every feature, calculates measurements (area for polygons, length for lines), and exposes the results through a REST API.

Built with:
- **FastAPI** for the web framework
- **GeoPandas** and **pyogrio** for reading geospatial data
- **Shapely** for geometry operations
- **PyProj** for coordinate reference system transformations
- **SQLAlchemy** with SQLite for data storage
- **Pydantic** for data validation and settings management

## Setup

### Prerequisites
- Python 3.11+
- pip
- GDAL system dependencies (for GeoPandas)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd geospatial-file-measurement-api
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Copy `.env.example` to `.env` and adjust as needed:
   ```bash
   cp .env.example .env
   ```

5. Initialize the database:
   ```bash
   python -c "from app.db.session import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

### Running the Service

Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

### Running Tests

Run the test suite with:
```bash
pytest
```

### Docker (Optional)

Build and run with Docker:
```bash
docker build -t geospatial-file-measurement-api .
docker run -p 8000:8000 geospatial-file-measurement-api
```

## API

### Upload a File

**Endpoint:** `POST /api/files/`

**Request:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/files/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/file.zip;type=application/zip'
```

**Response (201 Created):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "filename": "file.zip",
  "feature_count": 5,
  "crs": "EPSG:4326",
  "status": "completed",
  "error_message": null,
  "created_at": "2026-10-08T12:34:56.789Z"
}
```

### Get File Information

**Endpoint:** `GET /api/files/{id}/`

**Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "filename": "file.zip",
  "feature_count": 5,
  "crs": "EPSG:4326",
  "status": "completed",
  "error_message": null,
  "created_at": "2026-10-08T12:34:56.789Z"
}
```

### Get Feature Measurements

**Endpoint:** `GET /api/files/{id}/measurements/`

**Query Parameters:**
- `limit` (default: 100) - maximum number of features to return
- `offset` (default: 0) - number of features to skip

**Response (200 OK):**
```json
{
  "features": [
    {
      "index": 0,
      "geometry_type": "Polygon",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 0.009], [0.009, 0.009], [0.009, 0], [0, 0]]]
      },
      "crs": "EPSG:4326",
      "properties": {
        "id": 1,
        "name": "Test Polygon"
      },
      "measurement": {
        "supported": true,
        "type": "area",
        "value": 10000.0,
        "unit": "square_meters",
        "projected_crs": "EPSG:32633"
      }
    }
  ],
  "summary": {
    "total_area": 10000.0,
    "total_area_ha": 1.0,
    "total_area_sq_km": 0.01,
    "total_length": 0.0,
    "total_length_km": 0.0,
    "geometry_type_counts": {
      "Polygon": 1
    }
  },
  "limit": 100,
  "offset": 0,
  "total": 1
}
```

**Error Responses:**
- `404 Not Found`: File not found
- `409 Conflict`: File is not completed (status is processing or failed)
- `413 Payload Too Large`: File exceeds size limit
- `415 Unsupported Media Type`: Invalid file extension
- `400 Bad Request`: Invalid or corrupt file

## Real Examples

### Example 1: Upload and Measure a KML File

**Step 1: Upload the KML file**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/files/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@samples/sample.kml;type=application/vnd.google-earth.kml+xml'
```

**Response:**
```json
{
  "id": "81ca67ee-6a1e-4db1-808c-da4ea058c645",
  "filename": "sample.kml",
  "feature_count": 1,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-08T11:11:09"
}
```

**Step 2: Get file information**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/files/81ca67ee-6a1e-4db1-808c-da4ea058c645' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "id": "81ca67ee-6a1e-4db1-808c-da4ea058c645",
  "filename": "sample.kml",
  "feature_count": 1,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-08T11:11:09"
}
```

**Step 3: Get measurements**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/files/81ca67ee-6a1e-4db1-808c-da4ea058c645/measurements/' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "features": [
    {
      "index": 0,
      "geometry_type": "Point",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.0822035425683, 37.42228990140251, 0.0]
      },
      "crs": "EPSG:4326",
      "properties": {
        "id": null,
        "Name": "Sample Point",
        "description": null,
        "timestamp": null,
        "begin": null,
        "end": null,
        "altitudeMode": null,
        "tessellate": -1,
        "extrude": 0,
        "visibility": -1,
        "drawOrder": null,
        "icon": null
      },
      "measurement": {
        "supported": false,
        "type": null,
        "value": null,
        "unit": null,
        "projected_crs": null,
        "reason": "No measurement required for point features"
      }
    }
  ],
  "summary": {
    "total_area": 0.0,
    "total_area_ha": 0.0,
    "total_area_sq_km": 0.0,
    "total_length": 0.0,
    "total_length_km": 0.0,
    "geometry_type_counts": {
      "Point": 1
    }
  },
  "limit": 100,
  "offset": 0,
  "total": 1
}
```

### Example 2: Upload and Measure a Shapefile ZIP

**Step 1: Upload the shapefile ZIP**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/files/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@test_shapefile.zip;type=application/zip'
```

**Response:**
```json
{
  "id": "f337025f-215d-4736-98cf-bfdb9ac80776",
  "filename": "test_shapefile.zip",
  "feature_count": 1,
  "crs": "EPSG:4326",
  "status": "completed",
  "error_message": null,
  "created_at": "2026-10-08T08:27:34"
}
```

**Step 2: Get measurements**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/files/f337025f-215d-4736-98cf-bfdb9ac80776/measurements/' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "features": [
    {
      "index": 0,
      "geometry_type": "Polygon",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [0.0, 0.0],
          [0.0, 0.009],
          [0.009, 0.009],
          [0.009, 0.0],
          [0.0, 0.0]
        ]]
      },
      "crs": "EPSG:4326",
      "properties": {
        "id": 1
      },
      "measurement": {
        "supported": true,
        "type": "area",
        "value": 998983.8279138879,
        "unit": "square_meters",
        "projected_crs": "EPSG:32631",
        "reason": null
      }
    }
  ],
  "summary": {
    "total_area": 998983.8279138879,
    "total_area_ha": 99.8983827913888,
    "total_area_sq_km": 0.998983827913888,
    "total_length": 0.0,
    "total_length_km": 0.0,
    "geometry_type_counts": {
      "Polygon": 1
    }
  },
  "limit": 100,
  "offset": 0,
  "total": 1
}
```

### Example 3: Error Handling

**Upload a file with invalid extension**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/files/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@test.txt;type=text/plain'
```

**Response:**
```json
{
  "detail": "Unsupported file extension: .txt. Only .zip, .kml, and .wkt are allowed."
}
```

**Upload a file that exceeds the size limit**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/files/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@large.zip;type=application/zip'
```

**Response:**
```json
{
  "detail": "File size exceeds the limit of 52428800 bytes"
}
```

**Get information for a non-existent file**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/files/non-existent-id' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "detail": "File with ID non-existent-id not found"
}
```

To verify the service, we ran the API locally and tested with the provided sample files. The outputs were consistent with the examples shown above.

## Architecture

### Application Structure
```
app/
├── main.py                 # App factory and router registration
├── core/
│   └── config.py           # Settings management
├── api/
│   └── routes/
│       └── files.py        # API endpoints
├── schemas/                # Pydantic request/response models
├── models/                 # SQLAlchemy models
├── db/                     # Database session management
├── services/               # Business logic
│   ├── file_service.py     # Upload and processing orchestration
│   ├── parser.py           # File parsing (KML, Shapefile)
│   ├── crs.py              # CRS detection and projection selection
│   └── measurement.py      # Area/length calculation
└── utils/                  # Utilities (exceptions, etc.)
```

### File Processing Flow
1. **Upload**: File is saved to disk with a UUID filename
2. **Validation**: Extension, size, and basic structure validated
3. **Parsing**: File is read into a GeoDataFrame using GeoPandas
4. **CRS Handling**: Source CRS is extracted; if missing, error is returned
5. **Projection Selection**: Appropriate projected CRS is selected (UTM based on centroid)
6. **Measurement Calculation**: Area or length is calculated for each feature in the projected CRS
7. **Storage**: Results are saved to the database (PostgreSQL/SQLite)
8. **Response**: File information is returned to the client

### Measurement Calculation Flow
For each feature:
1. Check geometry validity and attempt to fix invalid polygons
2. Skip points (no measurement required)
3. For polygons: calculate area in the selected projected CRS
4. For linestrings: calculate length in the selected projected CRS
5. Handle multi-geometries by summing over parts
6. Return measurement with value, unit, and projected CRS used

### CRS Handling
- **Source CRS**: Extracted from file (.prj for Shapefile, always EPSG:4326 for KML)
- **Projection Selection**:
  - If source CRS is already projected and in meters, use it directly
  - If geographic (lat/lon), calculate UTM zone based on dataset centroid
  - Polar regions (lat > 84° or < -80°) use UPS projection
  - Fallback to equal-area projection if UTM cannot be determined
- **Measurement Units**: Area in square meters, length in meters (with convenience conversions)

## Design Decisions

### Synchronous Processing
Chose synchronous file processing (rather than background jobs with Celery/RQ) for simplicity and because the expected file sizes are small (≤50MB). For larger files or higher throughput, a job queue could be added.

### Database Choice
Used SQLAlchemy with SQLite for development simplicity, but designed to be swappable with PostgreSQL by changing the DATABASE_URL. For production with spatial queries, PostGIS would be a better choice.

### CRS Selection Strategy
Selected UTM as the default projected CRS for its widespread use and accuracy in mid-latitudes. Considered equal-area projections (like EPSG:6933) for area calculations but chose UTM for consistency between area and length measurements and simplicity of implementation.

### Geometry Storage
Store geometries as WKT in the database for simplicity and compatibility. Alternative would be GeoJSON or PostGIS geometry types.

### File Storage
Store uploaded original files in the filesystem with UUID filenames to avoid collisions and security issues. Metadata and measurements are stored in the database.

### Error Handling
Centralized exception handling with custom exception types mapped to appropriate HTTP status codes. All errors return a consistent JSON format.

### Validation
Used Pydantic v2 for request/response validation and settings management. File validation includes extension, size, and zip-slip protection.

## Learnings

- **Coordinate Reference Systems**: Proper handling of CRS is critical for accurate measurements. Never calculate area/length in geographic coordinates.
- **Geometry Validation**: Real-world geospatial data often contains invalid geometries; using `shapely.make_valid` helps recover from many issues.
- **File Security**: Protecting against zip-slip attacks is essential when extracting uploaded archives.
- **Performance**: For large feature counts, pagination is necessary to avoid overwhelming the client or server.
- **Type Safety**: Using type hints throughout the codebase significantly improves maintainability and catches errors early.

## Future Scope

- **Async Processing**: Add background job queue (Celery/RQ) for processing large files without blocking API requests.
- **PostGIS Support**: Replace SQLite with PostGIS for advanced spatial queries and indexing.
- **Additional Formats**: Support GeoPackage, GeoJSON, and other geospatial formats.
- **Geodesic Measurements**: Use `pyproj.Geod` for more accurate measurements on the ellipsoid, especially for large features.
- **Per-feature CRS Selection**: Instead of dataset-level CRS selection, compute UTM zone per feature for better accuracy when features span large areas.
- **Authentication & Rate Limiting**: Add API key authentication and rate limiting for production use.
- **Streaming Upload**: Implement streaming upload for very large files to minimize memory usage.
- **Caching**: Cache measurement results to avoid reprocessing the same file.
- **CI Pipeline**: Add GitHub Actions for automated testing and deployment.