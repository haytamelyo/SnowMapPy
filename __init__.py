# SnowMapPy Package
# A comprehensive package for MODIS snow cover time series processing

# Import core functionality
from .core import (
    save_as_zarr, optimal_combination, load_shapefile, load_dem_and_nanmask,
    clip_dem_to_roi, check_overlap, reproject_raster, reproject_shp, handle_reprojection,
    vectorized_interpolation_griddata_parallel,
    validate_modis_class, get_valid_modis_classes, get_invalid_modis_classes,
    extract_date, generate_file_lists, get_map_dimensions, generate_time_series
)

# Import local processing functionality
from .local import (
    modis_time_series, process_files_array, prepare_modis,
    extract_date as local_extract_date, generate_file_lists as local_generate_file_lists, 
    get_map_dimensions as local_get_map_dimensions
)

# Import cloud processing functionality
from .cloud import (
    modis_time_series_cloud, process_modis_ndsi_cloud, process_files_array as cloud_process_files_array,
    load_modis_cloud_data, initialize_earth_engine
)

__version__ = "2.0.0"

__all__ = [
    # Core functionality
    'save_as_zarr', 'optimal_combination', 'load_shapefile', 'load_dem_and_nanmask',
    'clip_dem_to_roi', 'check_overlap', 'reproject_raster', 'reproject_shp', 'handle_reprojection',
    'vectorized_interpolation_griddata_parallel',
    'validate_modis_class', 'get_valid_modis_classes', 'get_invalid_modis_classes',
    'extract_date', 'generate_file_lists', 'get_map_dimensions', 'generate_time_series',
    
    # Local processing
    'modis_time_series', 'process_files_array', 'prepare_modis',
    'local_extract_date', 'local_generate_file_lists', 'local_get_map_dimensions',
    
    # Cloud processing
    'modis_time_series_cloud', 'process_modis_ndsi_cloud', 'cloud_process_files_array',
    'load_modis_cloud_data', 'initialize_earth_engine',
]