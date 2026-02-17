"""
MODIS Cloud Processing Pipeline
================================

Process MODIS snow cover data from Google Earth Engine.

Implements a 6-day moving window algorithm for gap-filling:
    - 3 days before + current day + 2 days after
    - Terra/Aqua fusion with quality control
    - Elevation-based snow correction
    - Numba-accelerated interpolation

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 1.0.0
"""

import os
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
from typing import Literal, Optional, Tuple

# Import optimized modules
from ..core.data_io import save_as_zarr, load_dem_and_nanmask
from ..core.temporal import interpolate_temporal, get_interpolation_methods
from ..core.quality import get_invalid_modis_classes
from ..core.utils import generate_time_series
from ..core.console import (
    print_header, print_section, print_success, print_error, 
    print_info, print_config, print_banner, print_complete,
    print_warning, suppress_warnings, green, blue, dim
)
from .loader import load_modis_cloud_data

# Suppress warnings on module load
suppress_warnings()

# Import Numba kernels for maximum performance
from .._numba_kernels import (
    merge_terra_aqua_3d,
    apply_elevation_snow_correction,
    apply_spatial_snow_correction,
    apply_old_spatial_snow_correction,
    clip_values_3d,
    apply_nanmask_3d,
    INVALID_CLASSES
)


# Type alias for interpolation methods
InterpolationMethod = Literal["nearest", "linear", "cubic"]

# Type alias for spatial correction methods
# Technical names: elevation_mean (old), neighbor_based (new), none
# Internal mapping: old/elevation_mean, new/neighbor_based, none
SpatialCorrectionMethod = Literal["old", "new", "none", "elevation_mean", "neighbor_based"]


def _prepare_dem_data(dem_ds: xr.Dataset) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare DEM data and create nanmask.
    
    MEMORY OPTIMIZATION: Handles Dask-backed arrays by computing only
    the DEM slice needed, not the full time series if present.
    
    Parameters
    ----------
    dem_ds : xr.Dataset
        DEM dataset from Earth Engine (can be Dask-backed).
        
    Returns
    -------
    dem : np.ndarray
        2D elevation array (lat, lon).
    nanmask : np.ndarray
        2D boolean mask for invalid pixels.
    """
    # Transpose to (lat, lon, time) if needed
    if 'time' in dem_ds.dims:
        dem_ds = dem_ds.transpose('lat', 'lon', 'time')
        dem_ds = dem_ds.isel(time=0)
    
    # Get elevation data - handle Dask arrays
    dem_data = dem_ds['elevation']
    if hasattr(dem_data, 'data') and hasattr(dem_data.data, 'compute'):
        # Dask array - compute to numpy
        dem = dem_data.values.astype(np.float64)
    else:
        dem = dem_data.values.astype(np.float64)
    
    # Handle 3D case
    if dem.ndim == 3:
        dem = dem[:, :, 0]
    
    nanmask = np.isnan(dem)
    
    return dem, nanmask


def _load_or_create_nan_array(
    dataset: xr.Dataset,
    date: pd.Timestamp,
    shape: Tuple[int, int],
    var_name: str
) -> np.ndarray:
    """
    Load data for specific date or create NaN array if missing.
    
    MEMORY OPTIMIZATION: Handles both Dask-backed and numpy-backed arrays.
    For Dask arrays, only computes the specific time slice needed.
    
    This is a critical function called many times during processing.
    Optimized for fast date lookup with minimal memory footprint.
    
    Parameters
    ----------
    dataset : xr.Dataset
        Dataset containing the variable (can be Dask-backed).
    date : pd.Timestamp
        Date to extract.
    shape : tuple
        Shape of output array (lat, lon).
    var_name : str
        Variable name to extract.
        
    Returns
    -------
    np.ndarray
        Data for the date, or NaN array if date not available.
        Always returns a numpy array (not Dask).
    """
    date_str = date.strftime('%Y-%m-%d')
    
    # Fast check if date exists in dataset
    if date_str in dataset.time.values:
        data = dataset.sel(time=date_str)[var_name]
        
        # Handle Dask arrays: compute only this slice
        if hasattr(data, 'data') and hasattr(data.data, 'compute'):
            # Dask array - compute to numpy
            return data.values.astype(np.float64)
        else:
            # Already numpy
            return data.values.astype(np.float64)
    else:
        return np.full(shape, np.nan, dtype=np.float64)


def process_files_array(
    series: pd.DatetimeIndex,
    movwind: range,
    currentday_ind: int,
    mod_data: xr.Dataset,
    myd_data: xr.Dataset,
    mod_class_data: xr.Dataset,
    myd_class_data: xr.Dataset,
    dem: np.ndarray,
    nanmask: np.ndarray,
    daysbefore: int,
    daysafter: int,
    var_name: str,
    interpolation_method: InterpolationMethod = "nearest",
    spatial_correction_method: SpatialCorrectionMethod = "old",
    verbose: bool = True,
    save_pixel_counters: bool = False
) -> Tuple[np.ndarray, list, dict]:
    """
    Process MODIS time series using 6-day moving window approach with quality control.
    
    The moving window consists of 6 days:
        - 3 days BEFORE the current day
        - Current day (index 3 in window)
        - 2 days AFTER the current day
    
    This is the core processing function, heavily optimized with Numba.
    Supports both Dask-backed (lazy) and numpy-backed datasets.
    
    MEMORY OPTIMIZATION: Only the current 6-day window is materialized in RAM
    at any given time, enabling processing of multi-decade time series without
    running out of memory.
    
    Parameters
    ----------
    series : pd.DatetimeIndex
        Complete daily time series.
    movwind : range
        Moving window range (range(-3, 3) for 3 before, 2 after = 6 days total).
    currentday_ind : int
        Index of current day in the window (3 for 6-day window).
    mod_data : xr.Dataset
        Terra NDSI dataset (can be Dask-backed).
    myd_data : xr.Dataset
        Aqua NDSI dataset (can be Dask-backed).
    mod_class_data : xr.Dataset
        Terra quality class dataset (can be Dask-backed).
    myd_class_data : xr.Dataset
        Aqua quality class dataset (can be Dask-backed).
    dem : np.ndarray
        Digital Elevation Model (lat, lon).
    nanmask : np.ndarray
        Boolean mask for invalid pixels.
    daysbefore : int
        Number of days before current in window (3).
    daysafter : int
        Number of days after current in window (2).
    var_name : str
        Variable name for NDSI data.
    interpolation_method : str
        Interpolation method: "nearest", "linear", or "cubic".
    spatial_correction_method : str
        Spatial correction method:
        - "elevation_mean" or "old": Mean snow elevation method (recommended)
        - "neighbor_based" or "new": Checks surrounding pixels above 1000m
        - "none": No spatial correction
    verbose : bool
        Whether to print progress messages.
    save_pixel_counters : bool
        Whether to track pixel counters. Default False.
        
    Returns
    -------
    out_arr : np.ndarray
        Processed NDSI array (lat, lon, time).
    out_dates : list
        List of processed dates.
    counters : dict
        Dictionary with pixel counters for each date (empty if save_pixel_counters=False).
    """
    # Get dimensions
    mod_arr = mod_data[var_name].values
    lat_dim, lon_dim, _ = mod_arr.shape
    n_processed = len(series) - daysbefore - daysafter
    
    # Pre-allocate output array
    out_arr = np.empty((lat_dim, lon_dim, n_processed), dtype=np.float64)
    out_dates = []
    
    # Initialize counters dictionary
    counters = {
        'date': [],
        'original_nan_count': [],
        'spatial_filled_count': [],
        'temporal_filled_count': []
    }
    
    # Count total valid pixels inside ROI (not NaN from clipping)
    total_pixels_inside_roi = np.sum(~nanmask)
    
    # Get invalid classes as numpy array for Numba
    invalid_classes = np.array(get_invalid_modis_classes(), dtype=np.float64)
    
    # Window size
    window_size = len(movwind)
    
    # Progress bar
    iterator = range(daysbefore, len(series) - daysafter)
    if verbose:
        iterator = tqdm(iterator, desc="Processing MODIS time series")
    
    # Initialize window arrays (will be rolled efficiently)
    window_mod = None
    window_myd = None
    window_mod_class = None
    window_myd_class = None
    
    for i in iterator:
        if i == daysbefore:
            # Initialize moving window - load all window data
            window_mod = np.stack([
                _load_or_create_nan_array(mod_data, series[i + j], (lat_dim, lon_dim), var_name)
                for j in movwind
            ], axis=-1)
            window_myd = np.stack([
                _load_or_create_nan_array(myd_data, series[i + j], (lat_dim, lon_dim), var_name)
                for j in movwind
            ], axis=-1)
            window_mod_class = np.stack([
                _load_or_create_nan_array(mod_class_data, series[i + j], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class')
                for j in movwind
            ], axis=-1)
            window_myd_class = np.stack([
                _load_or_create_nan_array(myd_class_data, series[i + j], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class')
                for j in movwind
            ], axis=-1)
        else:
            # Roll window forward (efficient in-place operation)
            window_mod = np.roll(window_mod, -1, axis=2)
            window_myd = np.roll(window_myd, -1, axis=2)
            window_mod_class = np.roll(window_mod_class, -1, axis=2)
            window_myd_class = np.roll(window_myd_class, -1, axis=2)
            
            # Load new data for end of window
            window_mod[:, :, -1] = _load_or_create_nan_array(
                mod_data, series[i + daysafter], (lat_dim, lon_dim), var_name
            )
            window_myd[:, :, -1] = _load_or_create_nan_array(
                myd_data, series[i + daysafter], (lat_dim, lon_dim), var_name
            )
            window_mod_class[:, :, -1] = _load_or_create_nan_array(
                mod_class_data, series[i + daysafter], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class'
            )
            window_myd_class[:, :, -1] = _load_or_create_nan_array(
                myd_class_data, series[i + daysafter], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class'
            )
        
        # Apply DEM mask and invalid class mask to the original window arrays IN-PLACE
        # This matches the old behavior where masks persist across rolling iterations
        # Old code: window_mod[nanmask, :] = np.nan; window_mod[MOD_class_invalid] = np.nan
        
        # Apply DEM nanmask in-place (old: window_mod[nanmask, :] = np.nan)
        window_mod[nanmask, :] = np.nan
        window_myd[nanmask, :] = np.nan
        window_mod_class[nanmask, :] = np.nan
        window_myd_class[nanmask, :] = np.nan
        
        # Apply class-based invalid mask in-place (old: window_mod[MOD_class_invalid] = np.nan)
        MOD_class_invalid = np.isin(window_mod_class, invalid_classes)
        MYD_class_invalid = np.isin(window_myd_class, invalid_classes)
        window_mod[MOD_class_invalid] = np.nan
        window_myd[MYD_class_invalid] = np.nan
        
        # Merge Terra and Aqua with quality control
        # Old merge logic: MERGEind = np.isnan(window_mod) & ~np.isnan(window_myd)
        #                  NDSIFill_MERGE = np.where(MERGEind, window_myd, window_mod)
        merge_ind = np.isnan(window_mod) & ~np.isnan(window_myd)
        merged = np.where(merge_ind, window_myd, window_mod)
        
        # Get current day NDSI before interpolation
        ndsi_current = merged[:, :, currentday_ind].copy()
        
        # Count original NaN pixels INSIDE ROI (before spatial correction)
        # Only count NaN where nanmask is False (inside the shape)
        original_nan_inside_roi = np.sum(np.isnan(ndsi_current) & ~nanmask)
        
        # Apply spatial snow correction based on selected method
        # Support both technical names and legacy names
        spatial_filled = 0
        method_lower = spatial_correction_method.lower()
        if method_lower in ("new", "neighbor_based"):
            ndsi_current, spatial_filled = apply_spatial_snow_correction(
                ndsi_current, dem, window_size=5, min_elevation=1000.0
            )
        elif method_lower in ("old", "elevation_mean"):
            ndsi_current, spatial_filled = apply_old_spatial_snow_correction(
                ndsi_current, dem, threshold_elevation=1000.0
            )
        # else: "none" - no spatial correction applied
        
        # Update merged with corrected current day
        merged[:, :, currentday_ind] = ndsi_current
        
        # Set values > 100 to NaN (invalid NDSI values)
        merged = np.where(merged > 100, np.nan, merged)
        
        # Count NaN before temporal interpolation (inside ROI)
        nan_before_temporal = np.sum(np.isnan(merged[:, :, currentday_ind]) & ~nanmask)
        
        # Temporal interpolation using selected method (Numba-accelerated)
        merged = interpolate_temporal(merged, nanmask, method=interpolation_method)
        
        # Count NaN after temporal interpolation (inside ROI)
        nan_after_temporal = np.sum(np.isnan(merged[:, :, currentday_ind]) & ~nanmask)
        
        # Calculate temporal filled count
        temporal_filled = nan_before_temporal - nan_after_temporal
        
        # Clip to valid NDSI range [0, 100]
        merged = clip_values_3d(merged, 0.0, 100.0)
        
        # Extract current day result
        ndsi_final = merged[:, :, currentday_ind]
        
        # Set all pixels below 1000m elevation to 0 (no snow)
        # Snow is unlikely at low elevations, matching local processor behavior
        low_elevation_mask = dem < 1000
        ndsi_final[low_elevation_mask] = 0
        
        # Store result
        out_arr[:, :, i - daysbefore] = ndsi_final
        out_dates.append(series[i])
        
        # Store counters for this date (only if enabled)
        if save_pixel_counters:
            counters['date'].append(series[i].strftime('%Y-%m-%d'))
            counters['original_nan_count'].append(int(original_nan_inside_roi))
            counters['spatial_filled_count'].append(int(spatial_filled))
            counters['temporal_filled_count'].append(int(temporal_filled))
    
    return out_arr, out_dates, counters


# Valid output dtypes (float only, no integer types)
VALID_OUTPUT_DTYPES = ['float16', 'float32', 'float64']


def _validate_output_dtype(dtype: str) -> str:
    """
    Validate output dtype and return normalized value.
    
    Parameters
    ----------
    dtype : str
        Requested output dtype.
        
    Returns
    -------
    str
        Validated dtype string.
        
    Raises
    ------
    ValueError
        If dtype is invalid (integer types or unsupported float types).
    """
    dtype_lower = dtype.lower().strip()
    
    # Check for integer types and reject them
    integer_types = ['int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64']
    if dtype_lower in integer_types:
        raise ValueError(
            f"Invalid output_dtype '{dtype}'. Integer types are not supported because:\n"
            f"  - NDSI data requires NaN representation for missing values\n"
            f"  - Integer types cannot represent NaN\n"
            f"  - Minimum supported dtype is 'float16' (sufficient for NDSI range 0-100)\n"
            f"\nValid options: {', '.join(VALID_OUTPUT_DTYPES)}"
        )
    
    # Check for valid float types
    if dtype_lower not in VALID_OUTPUT_DTYPES:
        raise ValueError(
            f"Invalid output_dtype '{dtype}'.\n"
            f"Valid options: {', '.join(VALID_OUTPUT_DTYPES)}\n"
            f"Recommended: 'float16' (50% memory savings, sufficient for NDSI 0-100 range)"
        )
    
    return dtype_lower


def modis_time_series_cloud(
    mod_ds: xr.Dataset,
    myd_ds: xr.Dataset,
    mod_class_ds: xr.Dataset,
    myd_class_ds: xr.Dataset,
    dem_ds: xr.Dataset,
    output_zarr: str,
    file_name: str,
    var_name: str = 'NDSI_Snow_Cover',
    source: str = 'cloud',
    oparams_file: Optional[str] = None,
    interpolation_method: InterpolationMethod = "nearest",
    spatial_correction_method: SpatialCorrectionMethod = "old",
    verbose: bool = True,
    save_pixel_counters: bool = False,
    output_dtype: str = 'float16',
    target_crs: str = None
) -> Tuple[xr.Dataset, dict]:
    """
    Process MODIS time series and save to Zarr format.
    
    This is the main processing entry point for cloud data. It applies the
    6-day moving window gap-filling algorithm with Terra/Aqua fusion.
    
    Moving Window: 6 days total
        - 3 days before current day
        - Current day (target for gap-filling)
        - 2 days after current day
    
    MEMORY OPTIMIZATION: 
    - Uses float16 by default, reducing memory by 50%
    - Supports Dask-backed input arrays for lazy processing
    - Only materializes the current 6-day window in RAM
    
    Parameters
    ----------
    mod_ds : xr.Dataset
        Terra (MOD10A1) NDSI dataset (can be Dask-backed).
    myd_ds : xr.Dataset
        Aqua (MYD10A1) NDSI dataset (can be Dask-backed).
    mod_class_ds : xr.Dataset
        Terra quality class dataset (can be Dask-backed).
    myd_class_ds : xr.Dataset
        Aqua quality class dataset (can be Dask-backed).
    dem_ds : xr.Dataset
        Digital Elevation Model dataset (can be Dask-backed).
    output_zarr : str
        Output directory for Zarr store.
    file_name : str
        Name for output file.
    var_name : str
        Variable name for NDSI data (default: 'NDSI_Snow_Cover').
    source : str
        Data source identifier (default: 'cloud').
    oparams_file : str, optional
        Deprecated. Kept for backward compatibility, ignored.
    interpolation_method : str
        Temporal interpolation method. One of:
        - "nearest": Forward/backward fill (fastest, default)
        - "linear": Linear interpolation
        - "cubic": Cubic spline interpolation (smoothest)
    spatial_correction_method : str
        Spatial snow correction method. One of:
        - "elevation_mean" or "old": Mean snow elevation method (recommended)
        - "neighbor_based" or "new": Checks surrounding pixels above 1000m
        - "none": No spatial correction applied
    verbose : bool
        Print progress messages. Default True.
    save_pixel_counters : bool
        Save pixel counters to CSV. Default False.
    output_dtype : str
        Output data type: 'float16' (default, 50% memory savings), 
        'float32', or 'float64'.
        
    Returns
    -------
    Tuple[xr.Dataset, dict]
        Processed NDSI dataset and counters dictionary.
    """
    import gc
    
    # Validate output dtype (rejects integer types)
    output_dtype = _validate_output_dtype(output_dtype)
    
    # Validate interpolation method
    valid_methods = get_interpolation_methods()
    if interpolation_method.lower() not in valid_methods:
        raise ValueError(
            f"Invalid interpolation_method '{interpolation_method}'. "
            f"Must be one of: {valid_methods}"
        )
    
    # Validate spatial correction method
    valid_spatial = ["new", "old", "none", "elevation_mean", "neighbor_based"]
    if spatial_correction_method.lower() not in valid_spatial:
        raise ValueError(
            f"Invalid spatial_correction_method '{spatial_correction_method}'. "
            f"Must be one of: {valid_spatial}"
        )
    
    # Moving window parameters (fixed as per algorithm requirements)
    # 6-day window: 3 days before + current day + 2 days after
    daysbefore = 3
    daysafter = 2
    
    # Prepare DEM and nanmask
    dem, nanmask = _prepare_dem_data(dem_ds)
    
    # Default: assume Aqua is available (will be overwritten if not)
    aqua_available = True
    
    # Transpose datasets for cloud data (lat, lon, time)
    if source == 'cloud':
        mod_ds = mod_ds.transpose('lat', 'lon', 'time')
        mod_class_ds = mod_class_ds.transpose('lat', 'lon', 'time')
        
        # Handle case where Aqua data is not available (dates before July 2002)
        if myd_ds is not None:
            myd_ds = myd_ds.transpose('lat', 'lon', 'time')
            myd_class_ds = myd_class_ds.transpose('lat', 'lon', 'time')
            aqua_available = True
        else:
            # Create empty Aqua datasets matching Terra structure
            # This allows the algorithm to proceed unchanged - it will simply
            # not find any valid Aqua data and use only Terra
            if verbose:
                print_warning("Aqua data not available for this date range - using Terra only")
            myd_ds = mod_ds.copy(deep=False)
            myd_ds[var_name] = xr.full_like(mod_ds[var_name], np.nan)
            myd_class_ds = mod_class_ds.copy(deep=False)
            myd_class_ds['NDSI_Snow_Cover_Class'] = xr.full_like(
                mod_class_ds['NDSI_Snow_Cover_Class'], np.nan
            )
            aqua_available = False
    
    # Validate data
    if var_name not in mod_ds:
        raise ValueError(f"Terra dataset does not contain variable '{var_name}'.")
    if var_name not in myd_ds:
        raise ValueError(f"Aqua dataset does not contain variable '{var_name}'.")
    
    mod_shape = mod_ds[var_name].values.shape
    myd_shape = myd_ds[var_name].values.shape
    
    if mod_shape[:2] != myd_shape[:2]:
        raise ValueError(
            f"Terra and Aqua spatial dimensions do not match: "
            f"Terra {mod_shape[:2]} vs Aqua {myd_shape[:2]}"
        )
    
    # Generate time series
    series, movwind, currentday_ind = generate_time_series(
        mod_ds['time'].values, daysbefore, daysafter
    )
    
    # Standardize time format for efficient lookup
    mod_ds['time'] = mod_ds['time'].dt.strftime('%Y-%m-%d')
    myd_ds['time'] = myd_ds['time'].dt.strftime('%Y-%m-%d')
    mod_class_ds['time'] = mod_class_ds['time'].dt.strftime('%Y-%m-%d')
    myd_class_ds['time'] = myd_class_ds['time'].dt.strftime('%Y-%m-%d')
    
    # Process time series
    if verbose:
        print_info("Applying spatio-temporal gap-filling algorithm...")
    
    out_arr, out_dates, counters = process_files_array(
        series, movwind, currentday_ind,
        mod_ds, myd_ds, mod_class_ds, myd_class_ds,
        dem, nanmask, daysbefore, daysafter, var_name,
        interpolation_method=interpolation_method,
        spatial_correction_method=spatial_correction_method,
        verbose=verbose,
        save_pixel_counters=save_pixel_counters
    )
    
    # Memory cleanup: free input datasets after processing
    # Keep only lat/lon coords needed for output
    lat_coords = mod_ds["lat"].values.copy()
    lon_coords = mod_ds["lon"].values.copy()
    del mod_ds, myd_ds, mod_class_ds, myd_class_ds, dem, nanmask
    gc.collect()
    
    # Create professional metadata structure for scientific publications
    from datetime import datetime
    from pyproj import CRS
    
    processing_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Parse CRS for dynamic coordinate attribute generation
    crs_obj = CRS.from_user_input(target_crs) if target_crs else CRS.from_epsg(4326)
    
    # Determine coordinate attributes based on CRS type
    if crs_obj.is_geographic:
        # Geographic CRS (e.g., WGS84, NAD83)
        x_standard_name = "longitude"
        y_standard_name = "latitude"
        x_units = "degrees_east"
        y_units = "degrees_north"
        x_long_name = "longitude"
        y_long_name = "latitude"
        geospatial_x_units = "degrees_east"
        geospatial_y_units = "degrees_north"
    else:
        # Projected CRS (e.g., UTM, Lambert)
        x_standard_name = "projection_x_coordinate"
        y_standard_name = "projection_y_coordinate"
        # Dynamically get linear units from CRS (usually 'm', but could be 'US survey foot')
        linear_unit = crs_obj.axis_info[0].unit_name if crs_obj.axis_info else "m"
        x_units = linear_unit
        y_units = linear_unit
        x_long_name = "x coordinate of projection"
        y_long_name = "y coordinate of projection"
        geospatial_x_units = linear_unit
        geospatial_y_units = linear_unit
    
    # Global dataset attributes (CF-compliant and ACDD-compliant)
    # Adjust description based on whether Aqua data was available
    if aqua_available:
        data_source_summary = ("Daily gap-filled Normalized Difference Snow Index (NDSI) snow cover "
                              "derived from MODIS Terra (MOD10A1) and Aqua (MYD10A1) sensors using "
                              "SnowMapPy's 6-day moving window algorithm with Terra/Aqua fusion.")
        data_source = "MODIS/061/MOD10A1 (Terra), MODIS/061/MYD10A1 (Aqua) via Google Earth Engine"
        platform_info = "Terra, Aqua"
    else:
        data_source_summary = ("Daily gap-filled Normalized Difference Snow Index (NDSI) snow cover "
                              "derived from MODIS Terra (MOD10A1) sensor using "
                              "SnowMapPy's 6-day moving window algorithm (Terra only, Aqua not available for date range).")
        data_source = "MODIS/061/MOD10A1 (Terra) via Google Earth Engine"
        platform_info = "Terra"
    
    global_attrs = {
        # === Identification ===
        "title": "MODIS NDSI Snow Cover - Gap-Filled Time Series",
        "summary": data_source_summary,
        "keywords": "NDSI, snow cover, MODIS, Terra, Aqua, gap-filling, cryosphere, remote sensing",
        "id": file_name,
        
        # === Data Source ===
        "source": data_source,
        "platform": platform_info,
        "sensor": "MODIS (Moderate Resolution Imaging Spectroradiometer)",
        "product_version": "Collection 6.1",
        
        # === Processing Information ===
        "processing_level": "Level 3 (Gap-filled)",
        "processing_software": "SnowMapPy v1.0.0",
        "processing_software_url": "https://github.com/haytamelyo/SnowMapPy",
        "processing_method": "6-day moving window gap-filling (3 days before, current day, 2 days after)",
        "interpolation_method": interpolation_method,
        "spatial_correction_method": spatial_correction_method,
        "date_created": processing_timestamp,
        
        # === Spatial Information ===
        "geospatial_lat_min": float(np.nanmin(lat_coords)),
        "geospatial_lat_max": float(np.nanmax(lat_coords)),
        "geospatial_lon_min": float(np.nanmin(lon_coords)),
        "geospatial_lon_max": float(np.nanmax(lon_coords)),
        "geospatial_lat_units": geospatial_y_units,
        "geospatial_lon_units": geospatial_x_units,
        "crs": target_crs if target_crs else "EPSG:4326",
        "crs_wkt": crs_obj.to_wkt(),
        "spatial_resolution": "500m (MODIS native)",
        
        # === Temporal Information ===
        "time_coverage_start": out_dates[0].strftime('%Y-%m-%dT00:00:00Z'),
        "time_coverage_end": out_dates[-1].strftime('%Y-%m-%dT00:00:00Z'),
        "time_coverage_duration": f"P{len(out_dates)}D",
        "time_coverage_resolution": "P1D",
        
        # === Data Quality ===
        "quality_control": ("Invalid MODIS classes (cloud=50, lake ice=37, inland water=39, ocean=255) "
                          "masked prior to processing. Elevation mask applied below 1000m."),
        "elevation_threshold": "1000m (pixels below set to 0 NDSI)",
        "moving_window_days_before": daysbefore,
        "moving_window_days_after": daysafter,
        
        # === Technical Specifications ===
        "output_dtype": output_dtype,
        "compression": "ZSTD level 3",
        "storage_format": "Zarr v3",
        
        # === Attribution ===
        "creator_name": "SnowMapPy Development Team",
        "creator_url": "https://github.com/haytamelyo/SnowMapPy",
        "references": ("Elyoussfi, H., Bechri, H., & Bousbaa, M. (2025). SnowMapPy: A Python package "
                      "for MODIS snow cover gap-filling."),
        "license": "MIT License"
    }
    
    # Variable-specific attributes (CF-compliant)
    var_attrs = {
        "long_name": "MODIS/Terra+Aqua Normalized Difference Snow Index (NDSI) Snow Cover",
        "standard_name": "surface_snow_area_fraction",
        "units": "percent",
        "valid_min": 0,
        "valid_max": 100,
        "scale_factor": 1.0,
        "add_offset": 0.0,
        "grid_mapping": "spatial_ref",
        "_FillValue": np.nan,
        "coverage_content_type": "physicalMeasurement",
        "comment": ("Snow cover probability (0-100%) derived from the NDSI. "
                   "Processed via spatial-temporal gap-filling fusion.")
    }
    
    # Coordinate attributes (dynamically generated based on CRS)
    lat_attrs = {
        "long_name": y_long_name,
        "standard_name": y_standard_name,
        "units": y_units,
        "axis": "Y"
    }
    
    lon_attrs = {
        "long_name": x_long_name,
        "standard_name": x_standard_name,
        "units": x_units,
        "axis": "X"
    }
    
    time_attrs = {
        "long_name": "time",
        "standard_name": "time",
        "axis": "T"
        # Note: 'calendar' is automatically set by xarray during CF encoding
    }
    
    # Create output dataset with full metadata
    ds_out = xr.Dataset(
        {
            var_name: (("lat", "lon", "time"), out_arr, var_attrs)
        },
        coords={
            "lat": ("lat", lat_coords, lat_attrs),
            "lon": ("lon", lon_coords, lon_attrs),
            "time": ("time", out_dates, time_attrs)
        },
        attrs=global_attrs
    )
    
    # Write CRS using rioxarray for proper geospatial compatibility
    if target_crs:
        ds_out = ds_out.rio.write_crs(target_crs)
        ds_out = ds_out.rio.set_spatial_dims(x_dim="lon", y_dim="lat")
    
    # Free the large output array (data is now in ds_out)
    del out_arr
    gc.collect()
    
    # Save to Zarr with optimized compression
    if verbose:
        print_info(f"Saving to {file_name}.zarr...")
    
    save_as_zarr(ds_out, output_zarr, file_name, dtype=output_dtype)
    
    # Memory cleanup
    gc.collect()
    
    # Save counters to CSV if requested
    if save_pixel_counters and counters:
        counters_df = pd.DataFrame(counters)
        counters_csv_path = os.path.join(output_zarr, f"{file_name}_pixel_counters.csv")
        counters_df.to_csv(counters_csv_path, index=False)
        
        if verbose:
            print_success(f"Pixel counters saved")
    
    if verbose:
        print_success("Processing complete!")
    
    return ds_out, counters


def process_modis_ndsi_cloud(
    project_name: str,
    shapefile_path: str,
    start_date: str,
    end_date: str,
    output_path: str,
    file_name: Optional[str] = None,
    crs: str = "EPSG:4326",
    save_original_data: bool = False,
    terra_file_name: str = "MOD",
    aqua_file_name: str = "MYD",
    dem_file_name: str = "DEM",
    interpolation_method: InterpolationMethod = "nearest",
    spatial_correction_method: SpatialCorrectionMethod = "old",
    save_pixel_counters: bool = False,
    verbose: bool = True,
    output_dtype: str = 'float16'
) -> Tuple[xr.Dataset, dict]:
    """
    Complete cloud processing pipeline for MODIS NDSI data from Google Earth Engine.
    
    This is the main entry point for processing MODIS snow cover data. It handles:
    1. Loading data from Google Earth Engine (with server-side reprojection)
    2. Date validation against MODIS data availability (2000-02-24 onwards)
    3. Clipping to study area with Dask lazy loading
    4. Gap-filling using 6-day moving window (3 before + current + 2 after)
    5. Terra/Aqua sensor fusion
    6. Elevation-based snow correction
    7. Temporal interpolation
    8. Saving results to Zarr format (with memory-efficient dtype)
    9. Saving pixel counters to CSV
    
    MEMORY OPTIMIZATIONS:
    - Server-side reprojection on GEE (eliminates ~10GB local memory allocation)
    - Dask lazy loading (sortby, clip operations are lazy - no memory spike)
    - Streaming to Zarr for save_original_data (no full materialization)
    - Float16 output by default (50% memory savings)
    - Only the 6-day processing window is materialized in RAM
    
    Parameters
    ----------
    project_name : str
        Google Earth Engine project name for authentication.
    shapefile_path : str
        Path to shapefile defining the study area.
    start_date : str
        Start date in 'YYYY-MM-DD' format.
        Note: MODIS data starts from 2000-02-24. Earlier dates will be adjusted.
    end_date : str
        End date in 'YYYY-MM-DD' format.
        Note: Dates after latest available data will be adjusted.
    output_path : str
        Directory for output files.
    file_name : str, optional
        Name for output time series file. If None, defaults to
        '<shapefile_name>_NDSI' (e.g., 'study_area_NDSI').
    crs : str
        Coordinate reference system (default: 'EPSG:4326').
        Reprojection is handled on the GEE server - no local memory needed.
    save_original_data : bool
        Save original Terra/Aqua data before processing.
        With Dask lazy loading, this streams to disk without holding in RAM.
    terra_file_name : str
        Name for Terra data file if saving.
    aqua_file_name : str
        Name for Aqua data file if saving.
    dem_file_name : str
        Name for DEM file if saving.
    interpolation_method : str
        Temporal interpolation method:
        - "nearest": Forward/backward fill (fastest)
        - "linear": Linear interpolation
        - "cubic": Cubic spline interpolation
    spatial_correction_method : str
        Spatial snow correction method:
        - "elevation_mean" or "old": Mean snow elevation method (recommended)
        - "neighbor_based" or "new": Checks surrounding pixels above 1000m
        - "none": No spatial correction
    save_pixel_counters : bool
        Save pixel counters to CSV for debugging. Default False.
    verbose : bool
        Print progress messages.
    output_dtype : str
        Output data type: 'float16' (default, 50% memory savings), 
        'float32', or 'float64'. Float16 preserves NaN values and is 
        sufficient for NDSI data (0-100 range).
        
    Returns
    -------
    Tuple[xr.Dataset, dict]
        Processed NDSI time series dataset and pixel counters.
        
    Examples
    --------
    >>> from SnowMapPy import process_modis_ndsi_cloud
    >>> 
    >>> result, counters = process_modis_ndsi_cloud(
    ...     project_name="my-gee-project",
    ...     shapefile_path="study_area.shp",
    ...     start_date="2020-01-01",
    ...     end_date="2020-12-31",
    ...     output_path="./output",
    ...     crs="EPSG:32629",  # UTM Zone 29N - reprojected on GEE server
    ...     interpolation_method="linear",
    ...     spatial_correction_method="elevation_mean",
    ...     save_original_data=True,  # Streams to disk - memory efficient!
    ...     output_dtype="float16"  # 50% memory savings
    ... )
    """
    import gc
    
    # Validate output dtype (rejects integer types)
    output_dtype = _validate_output_dtype(output_dtype)
    
    # Default file_name to shapefile name + _NDSI
    if file_name is None:
        shapefile_basename = os.path.splitext(os.path.basename(shapefile_path))[0]
        file_name = f"{shapefile_basename}_NDSI"
    
    if verbose:
        print_banner()
        print_section("Processing Parameters")
        print_config("Study area", os.path.basename(shapefile_path))
        print_config("Date range", f"{start_date} to {end_date}")
        print_config("Output", f"{file_name}.zarr")
        print_config("Target CRS", crs)
        print_config("Interpolation", interpolation_method)
        print_config("Spatial correction", spatial_correction_method)
        print()
    
    # Load data from Google Earth Engine (reprojection happens on GEE server!)
    if verbose:
        print_info("Preparing MODIS Terra and Aqua collections...")
    
    (ds_terra_value_clipped, ds_aqua_value_clipped,
     ds_terra_class_clipped, ds_aqua_class_clipped,
     ds_dem_clipped, roi_checker) = load_modis_cloud_data(
        project_name, shapefile_path, start_date, end_date, crs
    )
    
    # Memory cleanup after loading
    gc.collect()
    
    # Standardize dimension order to (lat, lon, time) for ALL datasets
    # GEE/xee may return projected CRS data as (time, X, Y) which becomes
    # (time, lon, lat) after renaming. This must be standardized BEFORE
    # saving original data so it matches the processed output dimension order.
    spatial_dims = [d for d in ds_terra_value_clipped.dims if d != 'time']
    if list(ds_terra_value_clipped.dims).index(spatial_dims[0]) != 0 or \
       list(ds_terra_value_clipped.dims) != ['lat', 'lon', 'time']:
        target_order = ('lat', 'lon', 'time')
        ds_terra_value_clipped = ds_terra_value_clipped.transpose(*target_order)
        ds_terra_class_clipped = ds_terra_class_clipped.transpose(*target_order)
        # Only transpose Aqua if available
        if ds_aqua_value_clipped is not None:
            ds_aqua_value_clipped = ds_aqua_value_clipped.transpose(*target_order)
            ds_aqua_class_clipped = ds_aqua_class_clipped.transpose(*target_order)
        # DEM may have a singleton time dimension from GEE - squeeze it out first
        if 'time' in ds_dem_clipped.dims:
            ds_dem_clipped = ds_dem_clipped.isel(time=0, drop=True)
        # Now transpose DEM to (lat, lon)
        dem_dims = [d for d in ds_dem_clipped.dims if d in ('lat', 'lon')]
        if len(dem_dims) == 2 and list(ds_dem_clipped.dims) != ['lat', 'lon']:
            ds_dem_clipped = ds_dem_clipped.transpose('lat', 'lon')
    
    # Save original data if requested (streaming to Zarr)
    if save_original_data:
        if verbose:
            print_info("Saving original data...")
        
        # Rechunk to Zarr-compatible chunks
        n_lat = len(ds_terra_value_clipped.lat)
        n_lon = len(ds_terra_value_clipped.lon)
        n_time = len(ds_terra_value_clipped.time)
        zarr_chunks = {'lat': n_lat, 'lon': n_lon, 'time': min(64, n_time)}
        
        # Stream each dataset to Zarr
        ds_terra_value_clipped.chunk(zarr_chunks).to_zarr(
            os.path.join(output_path, f"{terra_file_name}.zarr"), mode="w"
        )
        gc.collect()
        
        if ds_aqua_value_clipped is not None:
            ds_aqua_value_clipped.chunk(zarr_chunks).to_zarr(
                os.path.join(output_path, f"{aqua_file_name}.zarr"), mode="w"
            )
            gc.collect()
        
        dem_zarr_chunks = {'lat': n_lat, 'lon': n_lon}
        ds_dem_clipped.chunk(dem_zarr_chunks).to_zarr(
            os.path.join(output_path, f"{dem_file_name}.zarr"), mode="w"
        )
        gc.collect()
        
        ds_terra_class_clipped.chunk(zarr_chunks).to_zarr(
            os.path.join(output_path, f"{terra_file_name}_class.zarr"), mode="w"
        )
        gc.collect()
        
        if ds_aqua_class_clipped is not None:
            ds_aqua_class_clipped.chunk(zarr_chunks).to_zarr(
                os.path.join(output_path, f"{aqua_file_name}_class.zarr"), mode="w"
            )
            gc.collect()
        
        if verbose:
            print_success("Original data saved")
    
    # Process time series
    if verbose:
        print_info("Running time series analysis...")
    
    time_series, counters = modis_time_series_cloud(
        ds_terra_value_clipped, ds_aqua_value_clipped,
        ds_terra_class_clipped, ds_aqua_class_clipped,
        ds_dem_clipped, output_path, file_name,
        var_name='NDSI_Snow_Cover',
        source='cloud',
        interpolation_method=interpolation_method,
        spatial_correction_method=spatial_correction_method,
        verbose=verbose,
        save_pixel_counters=save_pixel_counters,
        output_dtype=output_dtype,
        target_crs=crs
    )
    
    # Final memory cleanup
    gc.collect()
    
    if verbose:
        print_complete("Processing complete!")
    
    return time_series, counters