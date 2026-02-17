# Core Module

::: SnowMapPy
    options:
      show_root_heading: true
      show_source: true
      members:
        - process_modis_ndsi_cloud
        - __version__

---

## process_modis_ndsi_cloud

The main entry point for processing MODIS NDSI snow cover data.

### Signature

```python
def process_modis_ndsi_cloud(
    project_name: str,
    shapefile_path: str,
    start_date: str,
    end_date: str,
    output_path: str,
    interpolation_method: str = "nearest",
    spatial_correction_method: str = "elevation_mean",
    output_dtype: str = "float16",
    compression: str = "zstd",
    output_name: str | None = None,
) -> tuple[xarray.Dataset, dict]
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_name` | `str` | *required* | Google Cloud project ID for Earth Engine |
| `shapefile_path` | `str` | *required* | Path to study area shapefile |
| `start_date` | `str` | *required* | Start date in YYYY-MM-DD format |
| `end_date` | `str` | *required* | End date in YYYY-MM-DD format |
| `output_path` | `str` | *required* | Directory for output files |
| `interpolation_method` | `str` | `"nearest"` | Temporal interpolation method |
| `spatial_correction_method` | `str` | `"elevation_mean"` | DEM-based correction method |
| `output_dtype` | `str` | `"float16"` | Output array data type |
| `compression` | `str` | `"zstd"` | Zarr compression codec |
| `output_name` | `str \| None` | `None` | Custom output filename (without extension) |

### Returns

A tuple containing:

1. **`result`** (`xarray.Dataset`): Gap-filled snow cover dataset with:
    - `NDSI` data variable (time, y, x)
    - `time`, `x`, `y` coordinates
    - Processing metadata as attributes

2. **`counters`** (`dict`): Processing statistics dictionary

### Interpolation Methods

| Value | Description |
|-------|-------------|
| `"nearest"` | Nearest neighbor - fastest, preserves original values |
| `"linear"` | Linear interpolation - smooth, good for general use |
| `"cubic"` | Cubic spline - smoothest, best for continuous analysis |

### Spatial Correction Methods

| Value | Description |
|-------|-------------|
| `"none"` | No spatial correction applied |
| `"elevation_mean"` | DEM-based elevation threshold correction |

### Example

```python
from SnowMapPy import process_modis_ndsi_cloud

# Basic usage
result, counters = process_modis_ndsi_cloud(
    project_name="my-gee-project",
    shapefile_path="study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output"
)

# Advanced usage
result, counters = process_modis_ndsi_cloud(
    project_name="my-gee-project",
    shapefile_path="study_area.shp",
    start_date="2015-10-01",
    end_date="2020-09-30",
    output_path="./output",
    interpolation_method="linear",
    spatial_correction_method="elevation_mean",
    output_dtype="float32",
    compression="zstd",
    output_name="atlas_snow_cover"
)

# Access results
print(f"Processed {len(result.time)} days")
print(f"Shape: {result['NDSI'].shape}")
print(f"Interpolated: {counters['interpolated_pixels']} pixels")
```

### Raises

| Exception | Condition |
|-----------|-----------|
| `FileNotFoundError` | Shapefile not found |
| `ValueError` | Invalid date format or range |
| `ee.EEException` | Earth Engine authentication failure |

---

## __version__

Package version string.

```python
from SnowMapPy import __version__

print(__version__)  # "1.0.0"
```
