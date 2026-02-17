# SnowMapPy

[![PyPI version](https://badge.fury.io/py/SnowMapPy.svg)](https://pypi.org/project/SnowMapPy/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Python package for processing MODIS NDSI (Normalized Difference Snow Index) snow cover data from Google Earth Engine. SnowMapPy implements a scientifically validated 6-day moving window gap-filling algorithm for accurate Snow Cover Area (SCA) estimation.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command-Line Interface](#command-line-interface)
- [Algorithm](#algorithm)
- [Technical Specifications](#technical-specifications)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Citation](#citation)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Cloud Processing** | Direct integration with Google Earth Engine for MODIS data access |
| **Sensor Fusion** | Combines Terra (MOD10A1) and Aqua (MYD10A1) observations |
| **Gap-Filling** | 6-day moving window with quality-controlled interpolation |
| **Elevation Correction** | DEM-based snow detection for high-altitude gaps (>1000m) |
| **Memory Efficient** | Dask lazy loading with server-side GEE reprojection |
| **Optimized Storage** | Zarr format with ZSTD compression (level 3) |
| **Float16 Output** | 50% memory reduction while preserving NDSI precision |
| **Interactive CLI** | User-friendly command-line interface with guided prompts |
| **Progress Tracking** | Real-time progress bar during time series processing |

---

## Installation

### Requirements

- **Python**: 3.11 or higher
- **Memory**: 8 GB RAM minimum (16 GB recommended for large regions)
- **Internet**: Required for Google Earth Engine data access

### Install from PyPI

```bash
pip install SnowMapPy
```

### Install from Source

```bash
git clone https://github.com/haytamelyo/SnowMapPy.git
cd SnowMapPy
pip install -e .
```

### Google Earth Engine Setup

1. **Create a GEE account** at [earthengine.google.com](https://earthengine.google.com/)

2. **Create a Cloud Project** in [Google Cloud Console](https://console.cloud.google.com/)

3. **Authenticate**:
```bash
earthengine authenticate
```

4. **Verify**:
```python
import ee
ee.Initialize(project='your-project-name')
print("Authentication successful")
```

---

## Quick Start

### Python API

```python
from SnowMapPy import process_modis_ndsi_cloud

result, counters = process_modis_ndsi_cloud(
    project_name="your-gee-project",
    shapefile_path="study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output",
    crs="EPSG:32629",                        # Target CRS (server-side reprojection)
    interpolation_method="nearest",           # Options: nearest, linear, cubic
    spatial_correction_method="elevation_mean", # Options: elevation_mean, neighbor_based, none
    save_pixel_counters=True                  # Save gap-filling statistics
)

print(f"Processed {len(result.time)} days")
```

### Output Structure

```
output/
├── study_area_NDSI.zarr/           # Gap-filled NDSI time series
│   ├── NDSI_Snow_Cover/            # Values 0-100 (float16)
│   ├── lat/                        # Coordinates
│   ├── lon/
│   └── time/
├── study_area_NDSI_pixel_counters.csv  # Gap-filling statistics
├── MOD.zarr/                       # Original Terra data (optional)
├── MYD.zarr/                       # Original Aqua data (optional)
└── DEM.zarr/                       # Elevation data (optional)
```

---

## Command-Line Interface

### Interactive Mode

```bash
snowmappy
```

The wizard guides you through all configuration options.

### Command-Line Arguments

```bash
snowmappy \
    -p your-gee-project \
    -s study_area.shp \
    --start 2020-01-01 \
    --end 2020-12-31 \
    -o ./output
```

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --project` | GEE project name | Required |
| `-s, --shapefile` | Study area shapefile | Required |
| `--start` | Start date (YYYY-MM-DD) | Required |
| `--end` | End date (YYYY-MM-DD) | Required |
| `-o, --output` | Output directory | Required |
| `-n, --name` | Output filename | `<shapefile>_NDSI` |
| `-i, --interpolation` | Interpolation method | `nearest` |
| `--spatial-correction` | Spatial correction method | `elevation_mean` |
| `--crs` | Coordinate reference system | `EPSG:4326` |
| `--save-counters` | Save pixel counters | `False` |

---

## Algorithm

### 6-Day Moving Window

SnowMapPy processes each day using a 6-day temporal window:

```
Day Index:    -3    -2    -1     0    +1    +2
              ├─────┼─────┼─────┼─────┼─────┤
              │  3 days before  │  2 days after │
                         Current Day
```

The window configuration (3 days before + current + 2 days after) optimizes temporal coverage while preserving computational efficiency.

### Processing Pipeline

```
Terra MOD10A1  ──┐
                 ├──► Quality Control ──► Sensor Fusion ──► 6-Day Window
Aqua MYD10A1  ───┘                              │
                                                ▼
SRTM DEM ────────────────────────────► Spatial Correction
                                                │
                                                ▼
                                      Temporal Interpolation
                                                │
                                                ▼
                                         Zarr Output
```

### Quality Control

Invalid MODIS classes are masked before processing:

| Class | Description | Action |
|-------|-------------|--------|
| 50 | Cloud | Masked |
| 37 | Lake ice | Masked |
| 39 | Inland water | Masked |
| 255 | Ocean/Fill | Masked |

### Spatial Correction Methods

| Method | Description |
|--------|-------------|
| `elevation_mean` | Fill gaps above mean snow elevation with NDSI=100 (recommended) |
| `neighbor_based` | Fill based on snow presence in surrounding pixels above 1000m |
| `none` | No spatial correction |

### Interpolation Methods

| Method | Speed | Description |
|--------|-------|-------------|
| `nearest` | Fastest | Forward/backward fill (preserves extremes) |
| `linear` | Medium | Linear interpolation between valid observations |
| `cubic` | Slower | Cubic spline (smoothest transitions) |

---

## Technical Specifications

### Storage Format

SnowMapPy uses **Zarr v3** with **ZSTD compression** (level 3) for optimal storage:

- Chunked storage for efficient partial reads
- ZSTD provides ~60% compression ratio with fast decompression
- Cloud-optimized format compatible with Dask parallel computing

### Memory Optimization

| Technique | Benefit |
|-----------|---------|
| Server-side reprojection | Eliminates ~10GB local memory allocation |
| Dask lazy loading | Only 6-day window materialized in RAM |
| Float16 output | 50% memory reduction (sufficient for NDSI 0-100 range) |
| Streaming to Zarr | Original data saved without full materialization |

### Data Types

Output uses `float16` by default:
- Preserves NaN values for missing data
- Sufficient precision for NDSI range (0-100)
- 50% smaller than float32, 75% smaller than float64

---

## API Reference

### `process_modis_ndsi_cloud`

Main processing function for MODIS NDSI data.

```python
def process_modis_ndsi_cloud(
    project_name: str,
    shapefile_path: str,
    start_date: str,
    end_date: str,
    output_path: str,
    file_name: Optional[str] = None,
    crs: str = "EPSG:4326",
    save_original_data: bool = False,
    interpolation_method: str = "nearest",
    spatial_correction_method: str = "elevation_mean",
    save_pixel_counters: bool = False,
    verbose: bool = True,
    output_dtype: str = "float16"
) -> Tuple[xr.Dataset, dict]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_name` | str | GEE project name |
| `shapefile_path` | str | Path to study area shapefile |
| `start_date` | str | Start date (YYYY-MM-DD) |
| `end_date` | str | End date (YYYY-MM-DD) |
| `output_path` | str | Output directory |
| `file_name` | str | Output filename (default: `<shapefile>_NDSI`) |
| `crs` | str | Target CRS (default: EPSG:4326) |
| `save_original_data` | bool | Save Terra/Aqua/DEM data |
| `interpolation_method` | str | `nearest`, `linear`, or `cubic` |
| `spatial_correction_method` | str | `elevation_mean`, `neighbor_based`, or `none` |
| `save_pixel_counters` | bool | Save statistics to CSV |
| `output_dtype` | str | `float16`, `float32`, or `float64` |

**Returns:** Tuple of (xr.Dataset, dict) containing processed data and counters.

---

## Configuration

### Date Range

MODIS data availability:
- **Terra**: February 24, 2000 - present
- **Aqua**: July 4, 2002 - present

Dates outside availability are automatically adjusted.

### Performance Recommendations

For large study areas, process in yearly segments:

```python
for year in range(2010, 2021):
    process_modis_ndsi_cloud(
        project_name="your-project",
        shapefile_path="large_area.shp",
        start_date=f"{year}-01-01",
        end_date=f"{year}-12-31",
        output_path=f"./output/{year}"
    )
```

---

## Troubleshooting

### Authentication Error

```bash
# Re-authenticate with GEE
earthengine authenticate
```

### Memory Issues

- Process smaller time ranges (monthly instead of yearly)
- Reduce study area extent
- The package automatically uses memory-efficient processing

### Slow Downloads

Data download time scales with:
- Study area size
- Time range length
- GEE server load

### CRS Issues

Ensure shapefile has valid CRS:

```python
import geopandas as gpd
gdf = gpd.read_file("input.shp")
gdf = gdf.to_crs("EPSG:4326")
gdf.to_file("output.shp")
```

---

## Citation

```bibtex
@software{snowmappy2025,
  author       = {Elyoussfi, Haytam and Bechri, Hatim and Bousbaa, Mostafa},
  title        = {SnowMapPy: MODIS Snow Cover Processing for Google Earth Engine},
  year         = {2025},
  version      = {1.0.0},
  publisher    = {GitHub},
  url          = {https://github.com/haytamelyo/SnowMapPy}
}
```

### Related Publication

Bousbaa, M., et al. (2024). An accurate snow cover product for the Moroccan Atlas Mountains. *International Journal of Applied Earth Observation and Geoinformation*, 129, 103851. https://doi.org/10.1016/j.jag.2024.103851

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Authors

- **Haytam Elyoussfi** - Lead Developer - [haytam.elyoussfi@um6p.ma](mailto:haytam.elyoussfi@um6p.ma)
- **Hatim Bechri** - [hatim.bechri@uqtr.ca](mailto:hatim.bechri@uqtr.ca)
- **Mostafa Bousbaa** - [Mostafa.bousbaa@um6p.ma](mailto:Mostafa.bousbaa@um6p.ma)

---

<p align="center">
  <strong>SnowMapPy - Precision Snow Cover Mapping</strong>
</p>
