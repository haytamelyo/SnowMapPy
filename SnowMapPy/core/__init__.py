"""
SnowMapPy Core Module
====================

Shared functionality for MODIS NDSI data processing.

This module provides the building blocks used by both cloud and local
processing pipelines:
    - Data I/O with Zarr compression
    - Temporal gap-filling algorithms
    - Quality control using MODIS class values
    - Spatial operations and coordinate handling
    - Console utilities for colored output

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

from .data_io import (
    save_as_zarr,
    load_dem_and_nanmask,
    load_shapefile,
    load_zarr_dataset,
    optimal_combination  # Deprecated, kept for backward compatibility
)

from .spatial import (
    clip_dem_to_roi,
    check_overlap,
    reproject_raster,
    reproject_shp,
    handle_reprojection
)

from .temporal import (
    interpolate_temporal,
    get_interpolation_methods,
    validate_interpolation_method,
    vectorized_interpolation_griddata_parallel  # Deprecated legacy function
)

from .quality import (
    validate_modis_class,
    get_valid_modis_classes,
    get_invalid_modis_classes,
    create_modis_class_mask,
    apply_modis_quality_mask
)

from .utils import (
    extract_date,
    generate_file_lists,
    get_map_dimensions,
    generate_time_series
)

from .console import (
    suppress_warnings,
    print_banner,
    print_section,
    print_config,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_complete,
    green,
    red,
    blue,
    cyan,
    yellow,
    white,
    bold,
    dim
)


__all__ = [
    # Data I/O
    'save_as_zarr',
    'load_dem_and_nanmask',
    'load_shapefile',
    'load_zarr_dataset',
    'optimal_combination',
    
    # Spatial
    'clip_dem_to_roi',
    'check_overlap',
    'reproject_raster',
    'reproject_shp',
    'handle_reprojection',
    
    # Temporal
    'interpolate_temporal',
    'get_interpolation_methods',
    'validate_interpolation_method',
    'vectorized_interpolation_griddata_parallel',
    
    # Quality
    'validate_modis_class',
    'get_valid_modis_classes',
    'get_invalid_modis_classes',
    'create_modis_class_mask',
    'apply_modis_quality_mask',
    
    # Utils
    'extract_date',
    'generate_file_lists',
    'get_map_dimensions',
    'generate_time_series',
    
    # Console
    'suppress_warnings',
    'print_banner',
    'print_section',
    'print_config',
    'print_success',
    'print_error',
    'print_warning',
    'print_info',
    'print_complete',
    'green',
    'red',
    'blue',
    'cyan',
    'yellow',
    'white',
    'bold',
    'dim',
] 