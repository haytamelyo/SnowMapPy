# API Reference

Complete API documentation for SnowMapPy.

---

## Module Overview

SnowMapPy is organized into the following modules:

| Module | Description |
|--------|-------------|
| [`SnowMapPy`](../api/core.md) | Main package exports and entry points |
| [`SnowMapPy.cloud`](../api/cloud.md) | Google Earth Engine integration |
| [`SnowMapPy.core`](../api/core-utils.md) | Core utilities and processing functions |

---

## Quick Reference

### Main Processing Function

```python
from SnowMapPy import process_modis_ndsi_cloud

result, counters = process_modis_ndsi_cloud(
    project_name: str,              # GEE project ID
    shapefile_path: str,            # Path to study area shapefile
    start_date: str,                # Start date (YYYY-MM-DD)
    end_date: str,                  # End date (YYYY-MM-DD)
    output_path: str,               # Output directory
    interpolation_method: str = "nearest",     # "nearest", "linear", "cubic"
    spatial_correction_method: str = "elevation_mean",  # or "none"
    output_dtype: str = "float16",  # Output precision
    compression: str = "zstd",      # Compression codec
    output_name: str = None,        # Custom output name
)
```

### GEE Initialization

```python
from SnowMapPy.cloud import initialize_gee

initialize_gee(project: str)
```

### Direct Imports

```python
from SnowMapPy import (
    process_modis_ndsi_cloud,  # Main processing function
    __version__,               # Package version
)

from SnowMapPy.cloud import (
    initialize_gee,            # GEE authentication
    GEEDataLoader,             # Data loading class
    NDSIProcessor,             # Processing pipeline class
)

from SnowMapPy.core import (
    load_and_validate_shapefile,  # Shapefile utilities
    get_crs_from_shapefile,       # CRS detection
)
```

---

## Detailed Documentation

<div class="grid cards" markdown>

-   :material-package-variant:{ .lg .middle } **Core Module**

    ---

    Main package exports and the primary `process_modis_ndsi_cloud` function.
    
    [:octicons-arrow-right-24: View docs](core.md)

-   :material-cloud:{ .lg .middle } **Cloud Module**

    ---

    Google Earth Engine integration, data loading, and processing pipeline.
    
    [:octicons-arrow-right-24: View docs](cloud.md)

-   :material-tools:{ .lg .middle } **Core Utilities**

    ---

    Spatial operations, temporal processing, and helper functions.
    
    [:octicons-arrow-right-24: View docs](core-utils.md)

</div>

---

## Type Definitions

### Common Parameter Types

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_name` | `str` | Google Cloud project ID |
| `shapefile_path` | `str` | Path to `.shp` file |
| `start_date` | `str` | ISO format date (YYYY-MM-DD) |
| `end_date` | `str` | ISO format date (YYYY-MM-DD) |
| `output_path` | `str` | Directory path for output |

### Return Types

| Return | Type | Description |
|--------|------|-------------|
| `result` | `xarray.Dataset` | Gap-filled snow cover data |
| `counters` | `dict` | Processing statistics |

### Counters Dictionary

```python
counters = {
    'total_pixels': int,        # Total pixels processed
    'valid_pixels': int,        # Pixels with data
    'interpolated_pixels': int, # Gap-filled pixels
    'terra_pixels': int,        # Terra source pixels
    'aqua_pixels': int,         # Aqua source pixels
}
```
