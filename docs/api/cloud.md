# Cloud Module

::: SnowMapPy.cloud
    options:
      show_root_heading: true
      show_source: true

---

## Overview

The `SnowMapPy.cloud` module provides Google Earth Engine integration for data loading and processing.

---

## initialize_gee

Initialize Google Earth Engine with a project.

### Signature

```python
def initialize_gee(project: str) -> None
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project` | `str` | Google Cloud project ID |

### Example

```python
from SnowMapPy.cloud import initialize_gee

initialize_gee(project="my-gee-project")
```

### Notes

- Requires prior authentication via `earthengine authenticate`
- The project must have Earth Engine API enabled
- Can be called multiple times safely (idempotent)

---

## GEEDataLoader

Class for loading MODIS and DEM data from Google Earth Engine.

### Class Definition

```python
class GEEDataLoader:
    def __init__(
        self,
        project_name: str,
        shapefile_path: str,
        start_date: str,
        end_date: str,
        target_crs: str = "EPSG:4326"
    )
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_name` | `str` | *required* | GEE project ID |
| `shapefile_path` | `str` | *required* | Study area shapefile path |
| `start_date` | `str` | *required* | Start date (YYYY-MM-DD) |
| `end_date` | `str` | *required* | End date (YYYY-MM-DD) |
| `target_crs` | `str` | `"EPSG:4326"` | Target coordinate reference system |

### Methods

#### load_terra_data

Load MODIS Terra (MOD10A1) snow cover data.

```python
def load_terra_data(self) -> xarray.Dataset
```

#### load_aqua_data

Load MODIS Aqua (MYD10A1) snow cover data.

```python
def load_aqua_data(self) -> xarray.Dataset
```

#### load_dem_data

Load SRTM DEM data.

```python
def load_dem_data(self) -> xarray.DataArray
```

### Example

```python
from SnowMapPy.cloud import GEEDataLoader, initialize_gee

# Initialize GEE
initialize_gee("my-project")

# Create loader
loader = GEEDataLoader(
    project_name="my-project",
    shapefile_path="study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31"
)

# Load data
terra = loader.load_terra_data()
aqua = loader.load_aqua_data()
dem = loader.load_dem_data()

print(f"Terra shape: {terra['NDSI'].shape}")
print(f"Aqua shape: {aqua['NDSI'].shape}")
print(f"DEM shape: {dem.shape}")
```

---

## NDSIProcessor

Main processing pipeline class.

### Class Definition

```python
class NDSIProcessor:
    def __init__(
        self,
        interpolation_method: str = "nearest",
        spatial_correction_method: str = "elevation_mean",
        output_dtype: str = "float16"
    )
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interpolation_method` | `str` | `"nearest"` | Interpolation method |
| `spatial_correction_method` | `str` | `"elevation_mean"` | Spatial correction |
| `output_dtype` | `str` | `"float16"` | Output data type |

### Methods

#### process

Run the gap-filling pipeline.

```python
def process(
    self,
    terra_data: xarray.Dataset,
    aqua_data: xarray.Dataset,
    dem_data: xarray.DataArray,
    mask: numpy.ndarray
) -> tuple[xarray.Dataset, dict]
```

### Example

```python
from SnowMapPy.cloud import NDSIProcessor

processor = NDSIProcessor(
    interpolation_method="linear",
    spatial_correction_method="elevation_mean"
)

result, counters = processor.process(
    terra_data=terra,
    aqua_data=aqua,
    dem_data=dem,
    mask=study_area_mask
)
```

---

## Data Sources

### MODIS Snow Cover Products

| Product | Satellite | Collection | Resolution |
|---------|-----------|------------|------------|
| MOD10A1 | Terra | MODIS/006/MOD10A1 | 500m |
| MYD10A1 | Aqua | MODIS/006/MYD10A1 | 500m |

### DEM Data

| Product | Source | Resolution |
|---------|--------|------------|
| SRTM | USGS/SRTMGL1_003 | 30m |
