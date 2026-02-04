"""
SnowMapPy - MODIS Snow Cover Processing Package
================================================

High-performance processing of MODIS NDSI (Normalized Difference Snow Index)
data from Google Earth Engine with Numba JIT-compiled gap-filling algorithms.

This package implements a scientifically validated 5-day moving window 
algorithm for temporal gap-filling, combining Terra and Aqua observations 
with quality control based on the MODIS snow cover classification scheme.

Key Features:
    - Cloud processing via Google Earth Engine
    - Terra/Aqua sensor fusion with quality control
    - Temporal interpolation (nearest, linear, cubic)
    - Elevation-aware spatial snow correction (>1000m)
    - Fast Zarr output with ZSTD compression
    - Interactive command-line interface

Quick Start:
    >>> from SnowMapPy import process_modis_ndsi_cloud
    >>> result, counters = process_modis_ndsi_cloud(
    ...     project_name="your-gee-project",
    ...     shapefile_path="study_area.shp",
    ...     start_date="2020-01-01",
    ...     end_date="2020-12-31",
    ...     output_path="./output"
    ... )

Authors: Haytam Elyoussfi, Hatim Bechri, Mostafa Bousbaa
Version: 2.0.0
License: MIT
Repository: https://github.com/haytamelyo/SnowMapPy
"""

__version__ = "2.0.0"
__author__ = "Haytam Elyoussfi, Hatim Bechri, Mostafa Bousbaa"
__email__ = "haytam.elyoussfi@um6p.ma"
__license__ = "MIT"

# Suppress warnings early - before other imports
import warnings
warnings.filterwarnings('ignore')

# Core functionality
from .core import (
    # Data I/O
    save_as_zarr,
    load_dem_and_nanmask,
    load_shapefile,
    load_zarr_dataset,
    
    # Spatial operations
    clip_dem_to_roi,
    check_overlap,
    reproject_raster,
    reproject_shp,
    handle_reprojection,
    
    # Temporal interpolation
    interpolate_temporal,
    get_interpolation_methods,
    validate_interpolation_method,
    
    # Quality control
    validate_modis_class,
    get_valid_modis_classes,
    get_invalid_modis_classes,
    create_modis_class_mask,
    apply_modis_quality_mask,
    
    # Utilities
    extract_date,
    generate_file_lists,
    get_map_dimensions,
    generate_time_series
)

# Cloud processing (main entry points)
from .cloud import (
    modis_time_series_cloud,
    process_modis_ndsi_cloud,
    process_files_array,
    load_modis_cloud_data,
    initialize_earth_engine
)

# Expose Numba kernels for advanced users
from ._numba_kernels import (
    interpolate_nearest_3d,
    interpolate_linear_3d,
    interpolate_cubic_3d,
    merge_terra_aqua_3d,
    apply_elevation_snow_correction,
    apply_spatial_snow_correction,
    clip_values_3d,
    apply_nanmask_3d,
    INVALID_CLASSES
)


__all__ = [
    # Version info
    '__version__',
    '__author__',
    
    # Main entry points
    'process_modis_ndsi_cloud',
    'modis_time_series_cloud',
    
    # Core - Data I/O
    'save_as_zarr',
    'load_dem_and_nanmask',
    'load_shapefile',
    'load_zarr_dataset',
    
    # Core - Spatial
    'clip_dem_to_roi',
    'check_overlap',
    'reproject_raster',
    'reproject_shp',
    'handle_reprojection',
    
    # Core - Temporal
    'interpolate_temporal',
    'get_interpolation_methods',
    'validate_interpolation_method',
    
    # Core - Quality
    'validate_modis_class',
    'get_valid_modis_classes',
    'get_invalid_modis_classes',
    'create_modis_class_mask',
    'apply_modis_quality_mask',
    
    # Core - Utils
    'extract_date',
    'generate_file_lists',
    'get_map_dimensions',
    'generate_time_series',
    
    # Cloud
    'process_files_array',
    'load_modis_cloud_data',
    'initialize_earth_engine',
    
    # Numba kernels (advanced)
    'interpolate_nearest_3d',
    'interpolate_linear_3d',
    'interpolate_cubic_3d',
    'merge_terra_aqua_3d',
    'apply_elevation_snow_correction',
    'apply_spatial_snow_correction',
    'clip_values_3d',
    'apply_nanmask_3d',
    'INVALID_CLASSES',
]