"""
Utility Functions
=================

Helper functions for file handling and date manipulation.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import os
import zarr
import datetime
import pandas as pd
import numpy as np
from typing import Tuple, Optional


# =============================================================================
# MODIS DATA AVAILABILITY CONSTANTS
# =============================================================================

# First available MODIS Terra (MOD10A1) snow cover data
MODIS_FIRST_AVAILABLE_DATE = "2000-02-24"
MODIS_TERRA_FIRST_AVAILABLE_DATE = "2000-02-24"

# First available MODIS Aqua (MYD10A1) snow cover data
# NOTE: Aqua satellite launched July 4, 2002 - data available after this date
MODIS_AQUA_FIRST_AVAILABLE_DATE = "2002-07-04"

# These will be set dynamically from GEE, but provide reasonable defaults
MODIS_DEFAULT_LAST_DATE = None  # Will be queried from GEE


def check_aqua_availability(start_date: str, end_date: str) -> dict:
    """
    Check if MODIS Aqua data is available for the given date range.
    
    MODIS Aqua (MYD10A1) data is only available from July 4, 2002 onwards.
    This function determines if Aqua data exists for the requested period.
    
    Parameters
    ----------
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
        
    Returns
    -------
    dict
        {
            'aqua_available': bool,  # True if any Aqua data exists in range
            'aqua_start_date': str or None,  # Effective start date for Aqua
            'aqua_end_date': str or None,  # Effective end date for Aqua
            'reason': str or None  # Explanation if not available
        }
    """
    aqua_first = pd.Timestamp(MODIS_AQUA_FIRST_AVAILABLE_DATE)
    start_dt = pd.Timestamp(start_date)
    end_dt = pd.Timestamp(end_date)
    
    # Case 1: Entire date range is before Aqua launch
    if end_dt < aqua_first:
        return {
            'aqua_available': False,
            'aqua_start_date': None,
            'aqua_end_date': None,
            'reason': f"Requested end date ({end_date}) is before MODIS Aqua launch date ({MODIS_AQUA_FIRST_AVAILABLE_DATE}). Only Terra data will be used."
        }
    
    # Case 2: Start date is before Aqua launch but end date is after
    if start_dt < aqua_first:
        return {
            'aqua_available': True,
            'aqua_start_date': MODIS_AQUA_FIRST_AVAILABLE_DATE,
            'aqua_end_date': end_date,
            'reason': f"Aqua data available from {MODIS_AQUA_FIRST_AVAILABLE_DATE} to {end_date} (partial coverage)."
        }
    
    # Case 3: Full date range has Aqua data
    return {
        'aqua_available': True,
        'aqua_start_date': start_date,
        'aqua_end_date': end_date,
        'reason': None
    }


def validate_modis_date_range(
    start_date: str,
    end_date: str,
    project_name: str = None,
    verbose: bool = True
) -> Tuple[str, str, bool]:
    """
    Validate and adjust date range for MODIS data availability.
    
    MODIS Terra/Aqua snow cover data (MOD10A1/MYD10A1) is available from
    2000-02-24 onwards. This function validates and adjusts dates accordingly.
    
    Parameters
    ----------
    start_date : str
        Requested start date in 'YYYY-MM-DD' format.
    end_date : str
        Requested end date in 'YYYY-MM-DD' format.
    project_name : str, optional
        GEE project name for querying latest available date.
    verbose : bool
        Print warnings/info messages.
        
    Returns
    -------
    Tuple[str, str, bool]
        (adjusted_start_date, adjusted_end_date, dates_were_adjusted)
        
    Raises
    ------
    ValueError
        If start_date is after end_date, or if date range is invalid.
    """
    from .console import print_warning, print_info, print_error
    
    # Parse dates
    try:
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
    except Exception as e:
        raise ValueError(f"Invalid date format. Use 'YYYY-MM-DD'. Error: {e}")
    
    # Check if start is before end
    if start_dt > end_dt:
        raise ValueError(
            f"Start date ({start_date}) cannot be after end date ({end_date})"
        )
    
    modis_first = pd.Timestamp(MODIS_FIRST_AVAILABLE_DATE)
    dates_adjusted = False
    
    # Check start date against MODIS availability
    if start_dt < modis_first:
        if verbose:
            print_warning(
                f"Requested start date ({start_date}) is before MODIS data availability."
            )
            print_info(
                f"  MODIS Terra/Aqua snow cover data starts from {MODIS_FIRST_AVAILABLE_DATE}"
            )
            print_info(
                f"  → Adjusting start date to {MODIS_FIRST_AVAILABLE_DATE}"
            )
        start_date = MODIS_FIRST_AVAILABLE_DATE
        start_dt = modis_first
        dates_adjusted = True
    
    # Check end date - query GEE for latest available if project provided
    if project_name:
        try:
            latest_date = _get_latest_modis_date(project_name)
            if latest_date:
                latest_dt = pd.Timestamp(latest_date)
                if end_dt > latest_dt:
                    if verbose:
                        print_warning(
                            f"Requested end date ({end_date}) is after latest available MODIS data."
                        )
                        print_info(
                            f"  Latest available MODIS image: {latest_date}"
                        )
                        print_info(
                            f"  → Adjusting end date to {latest_date}"
                        )
                    end_date = latest_date
                    dates_adjusted = True
        except Exception as e:
            # If we can't query GEE, just proceed with user's date
            if verbose:
                print_warning(f"Could not verify latest MODIS date: {e}")
    
    # Validate we have a valid range after adjustments
    final_start = pd.Timestamp(start_date)
    final_end = pd.Timestamp(end_date)
    
    if final_start > final_end:
        raise ValueError(
            f"After date adjustments, start date ({start_date}) is after "
            f"end date ({end_date}). Please check your date range."
        )
    
    # Check minimum date range for moving window (need at least 6 days)
    date_range_days = (final_end - final_start).days
    if date_range_days < 6:
        raise ValueError(
            f"Date range must be at least 6 days for the moving window algorithm. "
            f"Current range: {date_range_days} days ({start_date} to {end_date})"
        )
    
    return start_date, end_date, dates_adjusted


def _get_latest_modis_date(project_name: str) -> Optional[str]:
    """
    Query Google Earth Engine for the latest available MODIS snow cover image.
    
    Parameters
    ----------
    project_name : str
        GEE project name.
        
    Returns
    -------
    str or None
        Latest date in 'YYYY-MM-DD' format, or None if query fails.
    """
    try:
        import ee
        
        # Initialize if not already done
        try:
            ee.Initialize(project=project_name, opt_url='https://earthengine-highvolume.googleapis.com')
        except:
            pass
        
        # Query Terra collection for latest image
        terra = ee.ImageCollection('MODIS/061/MOD10A1')
        latest_image = terra.sort('system:time_start', False).first()
        
        # Get the date
        latest_time = latest_image.get('system:time_start').getInfo()
        if latest_time:
            latest_date = pd.Timestamp(latest_time, unit='ms').strftime('%Y-%m-%d')
            return latest_date
            
    except Exception:
        pass
    
    return None


def prompt_user_date_adjustment(
    original_date: str,
    adjusted_date: str,
    date_type: str = "end"
) -> bool:
    """
    Prompt user to accept date adjustment or cancel processing.
    
    Parameters
    ----------
    original_date : str
        Originally requested date.
    adjusted_date : str
        Suggested adjusted date.
    date_type : str
        Either "start" or "end".
        
    Returns
    -------
    bool
        True to continue with adjusted date, False to cancel.
    """
    from .console import print_warning, yellow, white, green, red
    
    print()
    print(yellow("=" * 60))
    print(f"  {white('DATE ADJUSTMENT REQUIRED')}")
    print(yellow("=" * 60))
    print(f"  Requested {date_type} date: {original_date}")
    print(f"  Available {date_type} date: {adjusted_date}")
    print()
    
    try:
        response = input(f"  Continue with {adjusted_date}? [{green('Y')}/{red('n')}]: ").strip().lower()
        if response in ('', 'y', 'yes'):
            return True
        else:
            return False
    except (EOFError, KeyboardInterrupt):
        return False


# =============================================================================
# OPTIMAL CHUNKING UTILITIES
# =============================================================================

def calculate_optimal_chunks(
    shape: Tuple[int, ...],
    dtype: np.dtype = np.float32,
    target_chunk_mb: float = 64.0,
    max_memory_gb: float = None
) -> Tuple[int, ...]:
    """
    Calculate optimal chunk sizes for Dask arrays based on data dimensions.
    
    Optimizes for:
    - Memory efficiency (chunks fit in L3 cache when possible)
    - Spatial locality (prioritize keeping spatial dims together)
    - Temporal access patterns (smaller time chunks for streaming)
    
    Parameters
    ----------
    shape : tuple
        Shape of the data array (lat, lon, time) or (lat, lon).
    dtype : numpy dtype
        Data type of the array.
    target_chunk_mb : float
        Target chunk size in megabytes. Default 64MB (good for most systems).
    max_memory_gb : float, optional
        Maximum available memory. If None, auto-detected.
        
    Returns
    -------
    tuple
        Optimal chunk sizes matching the input shape dimensions.
        
    Notes
    -----
    For MODIS data processing, we prioritize:
    1. Full spatial extent per chunk when possible (better for spatial ops)
    2. Smaller time chunks (enables streaming processing)
    3. Chunk sizes that divide evenly into data dimensions
    """
    if max_memory_gb is None:
        try:
            import psutil
            max_memory_gb = psutil.virtual_memory().available / (1024 ** 3)
        except ImportError:
            max_memory_gb = 8.0  # Conservative default
    
    # Calculate bytes per element
    dtype = np.dtype(dtype)
    bytes_per_element = dtype.itemsize
    
    # Target chunk size in elements
    target_elements = int((target_chunk_mb * 1024 * 1024) / bytes_per_element)
    
    if len(shape) == 3:
        lat_size, lon_size, time_size = shape
        spatial_elements = lat_size * lon_size
        
        # For MODIS-sized data (~500x600 pixels), keep full spatial extent per chunk
        # This avoids Zarr chunk boundary issues and is more efficient for spatial ops
        # Only chunk spatially if dimensions are very large (>1500 pixels)
        max_spatial_for_full_chunk = 1500
        
        if lat_size <= max_spatial_for_full_chunk and lon_size <= max_spatial_for_full_chunk:
            # Use full spatial extent, chunk only time
            lat_chunk = lat_size
            lon_chunk = lon_size
            time_chunk = max(1, min(time_size, target_elements // spatial_elements))
            # Round time to nice numbers that divide evenly or leave small remainder
            time_chunk = _round_to_zarr_compatible_chunk(time_chunk, time_size)
        elif spatial_elements <= target_elements:
            # Small spatial extent: use full spatial, chunk time
            lat_chunk = lat_size
            lon_chunk = lon_size
            time_chunk = max(1, min(time_size, target_elements // spatial_elements))
            time_chunk = _round_to_zarr_compatible_chunk(time_chunk, time_size)
        else:
            # Very large spatial extent: balance spatial and temporal
            # Aim for ~50 time steps per chunk for good streaming
            time_chunk = _round_to_zarr_compatible_chunk(min(50, time_size), time_size)
            remaining_elements = target_elements // time_chunk
            
            # Calculate spatial chunks that maintain aspect ratio
            aspect_ratio = lat_size / lon_size if lon_size > 0 else 1
            lon_chunk = int(np.sqrt(remaining_elements / aspect_ratio))
            lat_chunk = int(lon_chunk * aspect_ratio)
            
            # Ensure minimum chunk sizes and Zarr compatibility
            lat_chunk = _round_to_zarr_compatible_chunk(max(64, min(lat_size, lat_chunk)), lat_size)
            lon_chunk = _round_to_zarr_compatible_chunk(max(64, min(lon_size, lon_chunk)), lon_size)
        
        return (lat_chunk, lon_chunk, time_chunk)
    
    elif len(shape) == 2:
        lat_size, lon_size = shape
        # For 2D data (DEM), use larger spatial chunks
        chunk_size = int(np.sqrt(target_elements))
        lat_chunk = _round_to_zarr_compatible_chunk(min(lat_size, chunk_size), lat_size)
        lon_chunk = _round_to_zarr_compatible_chunk(min(lon_size, chunk_size), lon_size)
        return (lat_chunk, lon_chunk)
    
    else:
        # Fallback for other dimensions
        return tuple(min(s, 128) for s in shape)


def _round_to_zarr_compatible_chunk(chunk: int, dim_size: int) -> int:
    """
    Round chunk size to ensure Zarr compatibility.
    
    Zarr requires the final chunk to be <= the first chunk.
    This function ensures valid chunking by using the full dimension
    or a chunk size that results in a smaller (or equal) final chunk.
    
    Parameters
    ----------
    chunk : int
        Target chunk size.
    dim_size : int
        Total size of the dimension.
        
    Returns
    -------
    int
        Zarr-compatible chunk size.
    """
    if chunk >= dim_size:
        return dim_size
    
    # Nice chunk sizes (prefer these for memory alignment)
    nice_sizes = [32, 64, 128, 256, 512, 1024]
    
    # Find closest nice size that is Zarr-compatible
    for nice in nice_sizes:
        if nice >= chunk * 0.7 and nice <= chunk * 1.3:
            if nice <= dim_size:
                remainder = dim_size % nice
                # Check Zarr requirement: last chunk <= first chunk
                if remainder == 0 or remainder <= nice:
                    return nice
    
    # If no nice size fits, calculate a compatible chunk size
    # Round to nearest 32 first
    rounded = max(32, (chunk // 32) * 32)
    if rounded > dim_size:
        return dim_size
    
    # Verify Zarr compatibility
    remainder = dim_size % rounded
    if remainder == 0 or remainder <= rounded:
        return rounded
    
    # If still incompatible, try finding a divisor or use full dimension
    # For moderate-sized dimensions, just use the full size (simpler and safer)
    if dim_size <= 2000:
        return dim_size
    
    # For large dimensions, find a working chunk size
    # by incrementally reducing until we get a valid configuration
    for test_chunk in range(rounded, 31, -1):
        remainder = dim_size % test_chunk
        if remainder == 0 or remainder <= test_chunk:
            return test_chunk
    
    return dim_size  # Ultimate fallback


def estimate_memory_for_processing(
    n_time: int,
    n_lat: int,
    n_lon: int,
    save_original: bool = False,
    dtype: str = 'float32'
) -> dict:
    """
    Estimate memory requirements for SnowMapPy processing.
    
    Parameters
    ----------
    n_time : int
        Number of timesteps.
    n_lat : int
        Number of latitude pixels.
    n_lon : int
        Number of longitude pixels.
    save_original : bool
        Whether original data will be saved.
    dtype : str
        Output data type.
        
    Returns
    -------
    dict
        Memory estimates for different components.
    """
    dtype_sizes = {'float16': 2, 'float32': 4, 'float64': 8}
    bytes_per = dtype_sizes.get(dtype, 4)
    
    spatial_pixels = n_lat * n_lon
    total_pixels = spatial_pixels * n_time
    
    # Moving window: 6 days × 4 arrays (terra/aqua value/class) × spatial × float64
    window_bytes = 6 * 4 * spatial_pixels * 8
    
    # DEM: spatial × float64
    dem_bytes = spatial_pixels * 8
    
    # Output array (if kept in memory): full size
    output_bytes = total_pixels * bytes_per
    
    # With Dask lazy loading, we only materialize chunks at a time
    # Estimate peak with 50-timestep chunks per dataset
    chunk_time = min(50, n_time)
    chunk_bytes = chunk_time * spatial_pixels * 4  # float32 for processing
    
    # If saving original: 4 additional datasets streamed to disk
    # With Dask, these don't add to peak memory significantly
    
    results = {
        'window_buffer_gb': window_bytes / (1024**3),
        'dem_gb': dem_bytes / (1024**3),
        'output_gb': output_bytes / (1024**3),
        'chunk_peak_gb': chunk_bytes / (1024**3),
        'recommended_min_ram_gb': (window_bytes + dem_bytes + chunk_bytes * 2) / (1024**3),
        'with_dask_peak_gb': (window_bytes + dem_bytes + chunk_bytes * 4) / (1024**3),
        'without_dask_peak_gb': (total_pixels * 8 * 5 + window_bytes + dem_bytes) / (1024**3),
        'memory_savings_percent': 0
    }
    
    if results['without_dask_peak_gb'] > 0:
        results['memory_savings_percent'] = (
            (1 - results['with_dask_peak_gb'] / results['without_dask_peak_gb']) * 100
        )
    
    return results


def extract_date(filename):
    """Extract date from MODIS filename."""
    date_str = filename.split('_')[-1].split('.')[0]
    return datetime.datetime.strptime(date_str, '%Y-%m-%d')


def generate_file_lists(dir_MOD, dir_MYD):
    """Generate sorted lists of MOD and MYD zarr files."""
    MOD_file_name = os.path.basename(os.path.normpath(dir_MOD))
    MYD_file_name = os.path.basename(os.path.normpath(dir_MYD))
    MODfiles = sorted([f for f in os.listdir(dir_MOD) if f.endswith('.zarr') and f.startswith(MOD_file_name)])
    MYDfiles = sorted([f for f in os.listdir(dir_MYD) if f.endswith('.zarr') and f.startswith(MYD_file_name)])
    
    return MODfiles, MYDfiles


def get_map_dimensions(dir_MOD, dir_MYD, MODfiles, MYDfiles):
    """Get and validate map dimensions from MODIS files."""
    row_mod, col_mod = zarr.open(os.path.join(dir_MOD, MODfiles[0]), mode='r')['SCA'][:].shape
    row_myd, col_myd = zarr.open(os.path.join(dir_MYD, MYDfiles[0]), mode='r')['SCA'][:].shape

    if row_mod != row_myd or col_myd != col_myd:
        raise ValueError('MODIS files do not have the same dimensions')
    
    return row_mod, col_mod, row_myd, col_myd


def generate_time_series(mod_dates, daysbefore, daysafter):
    """Generate continuous daily time series and moving window parameters."""
    tstart = mod_dates[0]
    tend = mod_dates[-1]
    
    series = pd.date_range(tstart, tend, freq='D')
    movwind = range(-daysbefore, daysafter + 1)
    currentday_ind = movwind.index(0)
    
    return series, movwind, currentday_ind