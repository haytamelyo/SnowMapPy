# SnowMapPy 🌨️

[![PyPI version](https://badge.fury.io/py/SnowMapPy.svg)](https://badge.fury.io/py/SnowMapPy)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python package for processing MODIS NDSI (Normalized Difference Snow Index) data from Google Earth Engine. SnowMapPy implements peer-reviewed gap-filling algorithms for accurate Snow Cover Area (SCA) estimation in mountainous regions.

---

## 📋 Table of Contents

- [Scientific Background](#-scientific-background)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Command-Line Interface](#-command-line-interface)
- [Algorithm Description](#-algorithm-description)
- [Package Structure](#-package-structure)
- [API Reference](#-api-reference)
- [Configuration Options](#-configuration-options)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Citation](#-citation)
- [License](#-license)

---

## 🔬 Scientific Background

### The Snow Cover Mapping Challenge

Accurate snow cover mapping is essential for:
- **Hydrological modeling**: Snow is a critical water reservoir, particularly in mountainous regions
- **Climate change monitoring**: Snow cover extent serves as an indicator of climate variability
- **Water resource management**: Snowmelt timing affects irrigation, hydropower, and flood forecasting
- **Ecosystem studies**: Snow cover influences vegetation phenology and wildlife behavior

### MODIS NDSI Data

The **Normalized Difference Snow Index (NDSI)** is calculated as:

$$NDSI = \frac{Green - SWIR}{Green + SWIR}$$

Where:
- **Green** = MODIS Band 4 (0.545–0.565 µm)
- **SWIR** = MODIS Band 6 (1.628–1.652 µm)

NDSI values range from -1 to 1, with values > 0.4 typically indicating snow-covered pixels.

### The Gap-Filling Problem

MODIS observations suffer from systematic data gaps due to:
- **Cloud contamination** (primary source, ~50% of observations affected globally)
- **Sensor viewing geometry** (edge-of-swath effects)
- **Data transmission errors**
- **Atmospheric conditions** (aerosols, thin clouds)

SnowMapPy addresses these gaps through a scientifically validated approach combining:
1. **Terra/Aqua sensor fusion** (morning + afternoon observations)
2. **Multi-day temporal compositing** (5-day moving window)
3. **Quality-controlled filtering** (MODIS class-based masking)
4. **Elevation-aware spatial correction** (DEM-based snow fill)

### Scientific Foundation

The algorithms implemented in SnowMapPy are based on methodologies validated in peer-reviewed literature for snow cover mapping in mountainous regions, including applications in the Atlas Mountains (Morocco).

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌐 **Cloud Processing** | Direct integration with Google Earth Engine for MODIS data access |
| 🔄 **Sensor Fusion** | Combines Terra (MOD10A1) and Aqua (MYD10A1) for maximum coverage |
| 🔍 **Quality Control** | MODIS NDSI_Snow_Cover_Class filtering removes clouds and errors |
| ⏰ **Gap Filling** | Three interpolation methods: nearest-neighbor, linear, cubic spline |
| 🏔️ **Elevation Correction** | DEM-based snow fill for high-altitude gaps above 1000m |
| 📊 **Zarr Output** | Efficient compressed storage for large time series |
| 🖥️ **Interactive CLI** | User-friendly command-line interface with guided prompts |
| 📈 **Pixel Counters** | Optional diagnostics for tracking gap-filling statistics |

---

## 🚀 Installation

### System Requirements

- **Python**: 3.11 or higher
- **Memory**: 8 GB RAM recommended (16 GB for large regions)
- **Storage**: Varies by study area and time range
- **Internet**: Required for Google Earth Engine data access

### Option 1: Install from PyPI (Recommended)

```bash
pip install SnowMapPy
```

### Option 2: Install from Source

```bash
git clone https://github.com/haytamelyo/SnowMapPy.git
cd SnowMapPy
pip install -e .
```

### Option 3: Using Conda

```bash
conda create -n snowmappy python=3.11
conda activate snowmappy
pip install SnowMapPy
```

### Google Earth Engine Setup

1. **Create a GEE account** at [earthengine.google.com](https://earthengine.google.com/)

2. **Create a Cloud Project** in [Google Cloud Console](https://console.cloud.google.com/)

3. **Authenticate**:
```bash
earthengine authenticate
```

4. **Verify authentication**:
```python
import ee
ee.Initialize(project='your-project-name')
print("GEE authenticated successfully!")
```

---

## 🎯 Quick Start

### Python API

```python
from SnowMapPy import process_modis_ndsi_cloud

# Process MODIS NDSI data for your study area
result, counters = process_modis_ndsi_cloud(
    project_name="your-gee-project",
    shapefile_path="path/to/study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output",
    # Optional parameters
    interpolation_method="nearest",      # 'nearest', 'linear', or 'cubic'
    spatial_correction_method="elevation_mean",  # 'elevation_mean', 'neighbor_based', or 'none'
    save_pixel_counters=True            # Save gap-filling statistics
)

print(f"Processed {len(result.time)} days of snow cover data")
```

### Output Structure

```
output/
├── study_area_NDSI.zarr/      # Main output (xarray-compatible)
│   ├── NDSI_Snow_Cover/       # Snow cover values (0-100)
│   ├── lat/                   # Latitude coordinates
│   ├── lon/                   # Longitude coordinates
│   └── time/                  # Time dimension
└── study_area_NDSI_pixel_counters.csv  # Gap-filling statistics (optional)
```

---

## 🖥️ Command-Line Interface

SnowMapPy provides an interactive CLI for ease of use.

### Interactive Mode (Recommended)

Simply run:
```bash
snowmappy
```

The wizard will guide you through:
1. GEE project configuration
2. Shapefile selection
3. Date range specification
4. Output settings
5. Processing options

### Command-Line Mode

For scripting and automation:

```bash
snowmappy \
    -p your-gee-project \
    -s path/to/shapefile.shp \
    --start 2020-01-01 \
    --end 2020-12-31 \
    -o ./output \
    --spatial-correction elevation_mean \
    --interpolation nearest
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --project` | GEE project name | (required) |
| `-s, --shapefile` | Path to study area shapefile | (required) |
| `--start` | Start date (YYYY-MM-DD) | (required) |
| `--end` | End date (YYYY-MM-DD) | (required) |
| `-o, --output` | Output directory | (required) |
| `-n, --name` | Output filename | `<shapefile>_NDSI` |
| `-i, --interpolation` | Interpolation method | `nearest` |
| `--spatial-correction` | Spatial correction method | `elevation_mean` |
| `--save-counters` | Save pixel counters CSV | `False` |
| `--crs` | Coordinate reference system | `EPSG:4326` |

---

## 🧮 Algorithm Description

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SnowMapPy Pipeline                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   Terra     │    │    Aqua     │    │    SRTM     │                 │
│  │  MOD10A1    │    │   MYD10A1   │    │     DEM     │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────────────────────────────────────────────┐               │
│  │              Quality Control Filtering              │               │
│  │    (Remove clouds, missing data, sensor errors)     │               │
│  └─────────────────────────┬───────────────────────────┘               │
│                            │                                           │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────┐               │
│  │              Terra/Aqua Sensor Fusion               │               │
│  │         (Prioritize morning Terra values)           │               │
│  └─────────────────────────┬───────────────────────────┘               │
│                            │                                           │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────┐               │
│  │          5-Day Moving Window Compositing            │               │
│  │    (±2 days for temporal gap coverage)              │               │
│  └─────────────────────────┬───────────────────────────┘               │
│                            │                                           │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────┐               │
│  │         Elevation-Based Spatial Correction          │               │
│  │   (Fill high-altitude gaps using DEM > 1000m)       │               │
│  └─────────────────────────┬───────────────────────────┘               │
│                            │                                           │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────┐               │
│  │            Temporal Interpolation                   │               │
│  │    (Backward-first priority: prefer past values)    │               │
│  └─────────────────────────┬───────────────────────────┘               │
│                            │                                           │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────┐               │
│  │              Output: Zarr + CSV Counters            │               │
│  └─────────────────────────────────────────────────────┘               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Quality Control Classes

MODIS NDSI_Snow_Cover_Class values used for filtering:

| Class | Description | Action |
|-------|-------------|--------|
| 0 | Snow-free land | ✅ Keep |
| 1 | Snow | ✅ Keep |
| 11 | Cloud | ❌ Mask |
| 25 | Missing data | ❌ Mask |
| 37 | Lake/inland water | ❌ Mask |
| 39 | Ocean | ❌ Mask |
| 50 | No decision | ❌ Mask |
| 100 | Night | ❌ Mask |
| 254 | Detector saturated | ❌ Mask |
| 255 | Fill value | ❌ Mask |

### Spatial Correction Methods

#### `elevation_mean` (Recommended)
Calculates the mean elevation of snow-covered pixels for each day. Pixels above this mean elevation with missing data are filled with snow (NDSI=100). This method is based on the physical principle that snow probability increases with elevation.

#### `neighbor_based`
Examines the 8-connected neighborhood of each pixel. If a majority of valid neighbors above 1000m are snow-covered, the center pixel is filled with snow.

#### `none`
No spatial correction applied. Only temporal interpolation is used.

### Interpolation Methods

| Method | Speed | Smoothness | Use Case |
|--------|-------|------------|----------|
| `nearest` | Fast | Low | Operational monitoring, preserves extremes |
| `linear` | Medium | Medium | General purpose, balanced approach |
| `cubic` | Slower | High | Research, smooth time series analysis |

---

## 📁 Package Structure

```
SnowMapPy/
├── __init__.py              # Package initialization and exports
├── cli.py                   # Interactive command-line interface
├── _numba_kernels.py        # JIT-compiled processing functions
├── cloud/                   # Google Earth Engine integration
│   ├── __init__.py
│   ├── auth.py              # GEE authentication utilities
│   ├── loader.py            # Parallel data loading from GEE
│   └── processor.py         # Main cloud processing pipeline
└── core/                    # Core functionality
    ├── __init__.py
    ├── console.py           # Console output formatting
    ├── data_io.py           # Data I/O operations (Zarr, shapefiles)
    ├── quality.py           # MODIS quality control functions
    ├── spatial.py           # Spatial operations (clipping, reprojection)
    ├── temporal.py          # Temporal interpolation algorithms
    └── utils.py             # Utility functions
```

---

## 📚 API Reference

### Main Functions

#### `process_modis_ndsi_cloud`

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
    verbose: bool = True
) -> Tuple[xr.Dataset, dict]:
    """
    Complete cloud processing pipeline for MODIS NDSI data.
    
    Parameters
    ----------
    project_name : str
        Google Earth Engine project name for authentication.
    shapefile_path : str
        Path to shapefile defining the study area.
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
    output_path : str
        Directory for output files.
    file_name : str, optional
        Output filename. Defaults to '<shapefile_name>_NDSI'.
    crs : str
        Coordinate reference system. Default: 'EPSG:4326'.
    save_original_data : bool
        Save raw Terra/Aqua data before processing.
    interpolation_method : str
        'nearest', 'linear', or 'cubic'.
    spatial_correction_method : str
        'elevation_mean', 'neighbor_based', or 'none'.
    save_pixel_counters : bool
        Save gap-filling statistics to CSV.
    verbose : bool
        Print progress messages.
        
    Returns
    -------
    Tuple[xr.Dataset, dict]
        Processed NDSI dataset and pixel counters dictionary.
    """
```

---

## ⚙️ Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EE_PROJECT` | Default GEE project name | None |
| `SNOWMAPPY_VERBOSE` | Enable verbose output | `True` |

### Performance Tips

For large study areas (> 10,000 km²), consider processing in yearly chunks:

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

## 🔧 Troubleshooting

### Common Issues

#### 1. Google Earth Engine Authentication

**Error**: `EEException: Invalid token` or "Please authenticate"

**Solution**:
```bash
earthengine authenticate
```

#### 2. Memory Errors

**Error**: `MemoryError` with large datasets

**Solution**:
- Process smaller time ranges (monthly instead of yearly)
- Reduce study area extent
- Increase system swap space

#### 3. Slow Downloads

**Issue**: Data loading takes very long

**Explanation**: GEE limits concurrent connections. Processing time scales approximately linearly with study area size and time range.

#### 4. CRS Mismatch

**Error**: "Shapefile has no coordinate reference system"

**Solution**: Ensure your shapefile includes a `.prj` file with valid CRS information:
```python
import geopandas as gpd
gdf = gpd.read_file("input.shp")
gdf = gdf.to_crs("EPSG:4326")
gdf.to_file("output.shp")
```

### Getting Help

1. Check [GitHub Issues](https://github.com/haytamelyo/SnowMapPy/issues)
2. Include: Python version, OS, complete error traceback
3. Provide a minimal reproducible example

---

## 🤝 Contributing

We welcome contributions!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/haytamelyo/SnowMapPy.git
cd SnowMapPy
pip install -e ".[dev]"
pytest tests/
```

---

## 📖 Citation

If you use SnowMapPy in your research, please cite:

```bibtex
@software{snowmappy2025,
  author       = {Elyoussfi, Haytam and Bechri, Hatim and Bousbaa, Mostafa},
  title        = {SnowMapPy: MODIS Snow Cover Processing for Google Earth Engine},
  year         = {2025},
  version      = {2.0.0},
  publisher    = {GitHub},
  url          = {https://github.com/haytamelyo/SnowMapPy}
}
```

### Related Publication

Bousbaa, M., Boudhar, A., Kinnard, C., Elyoussfi, H., Karaoui, I., Eljabiri, Y., Bouamri, H., & Chehbouni, A. (2024). An accurate snow cover product for the Moroccan Atlas Mountains: Optimization of the MODIS NDSI index threshold and development of snow fraction estimation models. *International Journal of Applied Earth Observation and Geoinformation*, 129, 103851. https://doi.org/10.1016/j.jag.2024.103851

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Haytam Elyoussfi** - *Lead Developer* - [haytam.elyoussfi@um6p.ma](mailto:haytam.elyoussfi@um6p.ma)
- **Hatim Bechri** - *Co-Author* - [hatim.bechri@uqtr.ca](mailto:hatim.bechri@uqtr.ca)
- **Mostafa Bousbaa** - *Co-Author* - [Mostafa.bousbaa@um6p.ma](mailto:Mostafa.bousbaa@um6p.ma)

---

<p align="center">
  <strong>Made with ❄️ for the snow hydrology research community</strong>
</p>
