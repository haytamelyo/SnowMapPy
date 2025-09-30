# SnowMapPy Docker Image

A comprehensive Python package for processing MODIS NDSI data from local files and Google Earth Engine, packaged in a ready-to-use Docker container.

## Quick Start

```bash
# Pull and run the image
docker run -it hatembe/snowmappy:latest

# Inside the container, test the package
python -c "import SnowMapPy; print('SnowMapPy is ready!')"
```

## What's Included

- **Python 3.11** with conda environment
- **SnowMapPy v1.0.5** - The main package
- **Geospatial libraries**: GDAL, rasterio, geopandas, pyproj, shapely
- **Earth Engine**: earthengine-api, geemap
- **Scientific computing**: numpy, scipy, pandas, xarray, zarr

## Usage Examples

```bash
# Basic usage
docker run -it hatembe/snowmappy:latest python -c "
from SnowMapPy.core.quality import get_invalid_modis_classes
print('Invalid MODIS classes:', get_invalid_modis_classes())
"

# Mount your data directory
docker run -v /path/to/your/data:/app/data -it hatembe/snowmappy:latest

# Run with Jupyter (if needed)
docker run -p 8888:8888 hatembe/snowmappy:latest jupyter lab --ip=0.0.0.0 --allow-root
```

## Package Information

- **Authors**: Haytam Elyoussfi, Hatim BECHRI
- **Version**: 1.0.5
- **License**: MIT
- **Source Code**: https://github.com/haytamelyo/SnowMapPy
- **PyPI**: https://pypi.org/project/SnowMapPy/
- **Docker Hub**: https://hub.docker.com/r/hatembe/snowmappy/

## Authors

- **Haytam Elyoussfi** - *Lead Developer* - [@haytamelyo](https://github.com/haytamelyo)
- **Hatim BECHRI** - *Co-Author* - [@Hbechri](https://github.com/Hbechri)

## Features

- Process MODIS NDSI data from local HDF files
- Cloud-based processing with Google Earth Engine
- Quality control and filtering functions
- Spatial and temporal analysis tools
- Export to various formats (zarr, netCDF, GeoTIFF)

## Requirements

- Docker Engine
- At least 4GB RAM recommended
- Internet connection for Google Earth Engine authentication