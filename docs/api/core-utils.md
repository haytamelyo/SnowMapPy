# Core Utilities

::: SnowMapPy.core
    options:
      show_root_heading: true
      show_source: true

---

## Overview

The `SnowMapPy.core` module provides utility functions for spatial operations, data I/O, and temporal processing.

---

## Spatial Utilities

### load_and_validate_shapefile

Load and validate a study area shapefile.

```python
def load_and_validate_shapefile(shapefile_path: str) -> geopandas.GeoDataFrame
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `shapefile_path` | `str` | Path to shapefile |

#### Returns

`geopandas.GeoDataFrame`: Validated geometry

#### Example

```python
from SnowMapPy.core import load_and_validate_shapefile

gdf = load_and_validate_shapefile("study_area.shp")
print(f"CRS: {gdf.crs}")
print(f"Bounds: {gdf.total_bounds}")
```

---

### get_crs_from_shapefile

Extract CRS from a shapefile.

```python
def get_crs_from_shapefile(shapefile_path: str) -> str
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `shapefile_path` | `str` | Path to shapefile |

#### Returns

`str`: CRS string (e.g., "EPSG:4326")

---

### create_mask_from_geometry

Create a binary mask from geometry.

```python
def create_mask_from_geometry(
    geometry: geopandas.GeoDataFrame,
    x_coords: numpy.ndarray,
    y_coords: numpy.ndarray
) -> numpy.ndarray
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `geometry` | `GeoDataFrame` | Study area geometry |
| `x_coords` | `ndarray` | X coordinate array |
| `y_coords` | `ndarray` | Y coordinate array |

#### Returns

`numpy.ndarray`: Boolean mask (True inside geometry)

---

## Data I/O

### save_to_zarr

Save dataset to Zarr format.

```python
def save_to_zarr(
    dataset: xarray.Dataset,
    output_path: str,
    compression: str = "zstd"
) -> None
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dataset` | `Dataset` | *required* | Data to save |
| `output_path` | `str` | *required* | Output file path |
| `compression` | `str` | `"zstd"` | Compression codec |

#### Example

```python
from SnowMapPy.core import save_to_zarr

save_to_zarr(
    dataset=result,
    output_path="./output/snow_cover.zarr",
    compression="zstd"
)
```

---

## Temporal Processing

### create_date_range

Create a date range for processing.

```python
def create_date_range(
    start_date: str,
    end_date: str
) -> pandas.DatetimeIndex
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | `str` | Start date (YYYY-MM-DD) |
| `end_date` | `str` | End date (YYYY-MM-DD) |

#### Returns

`pandas.DatetimeIndex`: Daily date range

---

## Quality Control

### apply_qa_filter

Apply MODIS QA filtering to snow cover data.

```python
def apply_qa_filter(
    data: numpy.ndarray,
    qa_band: numpy.ndarray
) -> numpy.ndarray
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `ndarray` | NDSI values |
| `qa_band` | `ndarray` | QA band values |

#### Returns

`numpy.ndarray`: Filtered data with invalid pixels masked

---

## Console Utilities

### print_processing_header

Print formatted processing header.

```python
def print_processing_header(
    version: str,
    params: dict
) -> None
```

---

## Memory Utilities

!!! note "Internal Use"
    
    Memory tracking utilities are available for debugging but not part of the public API.

```python
from SnowMapPy.core.memory import get_memory_usage_mb

current_mb = get_memory_usage_mb()
print(f"Current memory: {current_mb:.1f} MB")
```
