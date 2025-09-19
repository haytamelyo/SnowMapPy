# SnowMapPy 🌨️

A comprehensive Python package for processing MODIS NDSI (Normalized Difference Snow Index) data from both local files and Google Earth Engine, with advanced quality control and temporal interpolation capabilities.

## 📋 Table of Contents

- [✨ Features](#-features)
- [🚀 Installation](#-installation)
- [🎯 Quick Start](#-quick-start)
- [📁 Package Structure](#-package-structure)
- [📖 Usage Examples](#-usage-examples)
- [🧪 Testing](#-testing)
- [🔧 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

## ✨ Features

- **🌐 Cloud Processing**: Download and process MODIS NDSI data directly from Google Earth Engine
- **💾 Local Processing**: Process locally stored MODIS NDSI files
- **🔍 Quality Control**: Advanced masking using NDSI_Snow_Cover_Class for data validation
- **⏰ Temporal Interpolation**: Fill missing data points using spatial and temporal interpolation
- **🗺️ Spatial Operations**: Clip data to regions of interest using shapefiles or bounding boxes
- **📊 Data Export**: Save processed data in Zarr format for efficient storage and access

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Google Earth Engine account (for cloud processing)
- Required Python packages (automatically installed with the package)

### Option 1: Install from PyPI (Recommended)

```bash
pip install SnowMapPy
```

### Option 2: Install from GitHub

1. **Clone the repository:**
   ```bash
   git clone https://github.com/haytamelyo/SnowMapPy.git
   cd SnowMapPy/package
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```

### Google Earth Engine Setup (for cloud processing)

1. **Sign up for Google Earth Engine:**
   - Visit [https://earthengine.google.com/](https://earthengine.google.com/)
   - Sign up for an account

2. **Authenticate:**
   ```bash
   earthengine authenticate
   ```

## 🎯 Quick Start

### Cloud Processing Example

```python
from SnowMapPy.cloud.processor import process_modis_ndsi_cloud

# Process MODIS NDSI data from Google Earth Engine
result = process_modis_ndsi_cloud(
    project_name="your-gee-project",
    shapefile_path="path/to/roi.shp",
    start_date="2023-01-01",
    end_date="2023-01-31",
    output_path="output/",
    file_name="snow_cover"
)
```

### Local Processing Example

```python
from SnowMapPy.local.processor import process_modis_ndsi_local

# Process locally stored MODIS NDSI files
result = process_modis_ndsi_local(
    mod_dir="path/to/MOD/files/",
    myd_dir="path/to/MYD/files/",
    dem_file="path/to/dem.tif",
    output_path="output/",
    file_name="local_snow_cover"
)
```

## 📁 Package Structure

```
SnowMapPy/
├── core/                    # Shared functionality
│   ├── data_io.py          # Data input/output operations
│   ├── quality.py           # Quality control functions
│   ├── spatial.py           # Spatial operations
│   ├── temporal.py          # Temporal interpolation
│   └── utils.py             # Utility functions
├── cloud/                   # Google Earth Engine processing
│   ├── auth.py              # GEE authentication
│   ├── loader.py            # Data loading from GEE
│   └── processor.py         # Cloud processing pipeline
├── local/                   # Local file processing
│   ├── file_handler.py      # File management
│   ├── preparator.py        # Data preparation
│   └── processor.py         # Local processing pipeline
└── tests/                   # Test suite
    ├── test_core/           # Core functionality tests
    ├── test_cloud/          # Cloud processing tests
    └── test_local/          # Local processing tests
```

## 📖 Usage Examples

### Quality Control

```python
from SnowMapPy.core.quality import get_invalid_modis_classes, apply_modis_quality_mask

# Get invalid MODIS class values
invalid_classes = get_invalid_modis_classes()
print(f"Invalid classes: {invalid_classes}")

# Apply quality mask to data
masked_data = apply_modis_quality_mask(value_data, class_data)
```

### Spatial Operations

```python
from SnowMapPy.core.spatial import clip_dem_to_roi

# Clip DEM to region of interest
clipped_dem = clip_dem_to_roi(dem_data, shapefile_path)
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python tests/test_core/test_quality.py
python tests/test_cloud/test_basic_cloud.py
```

For detailed testing instructions, see [TESTING.md](TESTING.md).

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. **Google Earth Engine Authentication Required**
- **Error**: `EEException: Invalid token` or "Please authenticate"
- **Solution**: Run the authentication command and follow the browser prompts:
  ```bash
  earthengine authenticate
  ```
- **Note**: You need a Google Earth Engine account and access to a GEE project

#### 2. **Shapefile Missing Coordinate Reference System (CRS)**
- **Error**: "Shapefile has no coordinate reference system (CRS)"
- **Solution**: Your shapefile needs a proper CRS assigned. Open it in QGIS or ArcGIS and:
  - Set the correct CRS (e.g., WGS84, UTM zone, etc.)
  - Save the shapefile with the CRS information
- **Prevention**: Always ensure shapefiles have proper projection files (.prj)

#### 3. **Memory Errors with Large Datasets**
- **Error**: `MemoryError` or system freezing
- **Solution**: 
  - Reduce the date range (process monthly instead of yearly)
  - Use a smaller study area
  - Ensure you have at least 8GB RAM for large regions

#### 4. **Google Earth Engine Quota Exceeded**
- **Error**: `EEException: Quota exceeded`
- **Solution**: 
  - Reduce spatial or temporal extent of your request
  - Wait 24 hours for quota reset
  - Process data in smaller chunks

#### 5. **Package Installation Issues**
- **Error**: Import errors or dependency conflicts
- **Solution**: 
  - Use Python 3.8+ for best compatibility
  - Install in a clean virtual environment
  - On Windows, consider using conda for geospatial packages

#### 6. **Empty or Invalid Shapefiles**
- **Error**: "Shapefile is empty" or geometry errors
- **Solution**: 
  - Verify your shapefile contains valid geometries
  - Check that the shapefile covers your study area
  - Ensure all shapefile components (.shp, .shx, .dbf, .prj) are present

### Getting Help

If you encounter issues not covered here:
1. Check the [GitHub Issues](https://github.com/haytamelyo/SnowMapPy/issues) page
2. Include your Python version, operating system, and complete error message
3. Provide a minimal example that reproduces the problem

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Earth Engine team for providing the platform
- NASA for MODIS data
- The open-source geospatial community
