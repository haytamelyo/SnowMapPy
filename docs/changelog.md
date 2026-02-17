# Changelog

All notable changes to SnowMapPy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-17

### Initial Release

SnowMapPy is a high-performance Python package for processing MODIS NDSI snow cover data from Google Earth Engine with scientifically validated gap-filling algorithms.

### Features

- **Google Earth Engine Integration** - Direct cloud data access without local downloads
- **Server-Side Reprojection** - Data reprojection on GEE servers for reduced memory usage
- **Numba JIT Kernels** - High-performance interpolation (50-200x speedup over scipy)
- **Multiple Interpolation Methods** - `nearest`, `linear`, and `cubic` options
- **DEM-Based Spatial Correction** - Elevation-aware snow detection using SRTM
- **Zarr Output Format** - Cloud-optimized chunked storage with ZSTD compression
- **Float16 Support** - 50% memory reduction for output storage
- **Dask Lazy Loading** - Handle datasets larger than available RAM
- **Sensor Fusion** - Combines Terra (MOD10A1) and Aqua (MYD10A1) observations
- **6-Day Moving Window** - Temporal gap-filling (3 days before + current + 2 days after)
- **Command-Line Interface** - Full CLI for non-Python workflows
- **Quality Control** - MODIS QA flag filtering

### Authors

- **Haytam Elyoussfi** - Lead Developer
- **Hatim Bechri** - Co-Author
- **Mostafa Bousbaa** - Co-Author

---

## Reporting Issues

Found a bug? Please report it on [GitHub Issues](https://github.com/haytamelyo/SnowMapPy/issues).

Include:

- SnowMapPy version (`snowmappy --version`)
- Python version
- Operating system
- Minimal reproduction code
- Full error traceback
