"""
MODIS Cloud Processing Pipeline
================================

Process MODIS snow cover data from Google Earth Engine.

Implements a 5-day moving window algorithm for gap-filling:
    - 3 days before + current day + 2 days after
    - Terra/Aqua fusion with quality control
    - Elevation-based snow correction
    - Numba-accelerated interpolation

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
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
    suppress_warnings, green, blue, dim
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
    
    Parameters
    ----------
    dem_ds : xr.Dataset
        DEM dataset from Earth Engine.
        
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
    
    dem = dem_ds['elevation'].values.astype(np.float64)
    
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
    
    This is a critical function called many times during processing.
    Optimized for fast date lookup.
    
    Parameters
    ----------
    dataset : xr.Dataset
        Dataset containing the variable.
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
    """
    date_str = date.strftime('%Y-%m-%d')
    
    # Fast check if date exists in dataset
    if date_str in dataset.time.values:
        return dataset.sel(time=date_str)[var_name].values.astype(np.float64)
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
    Process MODIS time series using moving window approach with quality control.
    
    This is the core processing function, heavily optimized with Numba.
    
    Parameters
    ----------
    series : pd.DatetimeIndex
        Complete daily time series.
    movwind : range
        Moving window range (e.g., range(-3, 3) for 3 before, 2 after).
    currentday_ind : int
        Index of current day in the window.
    mod_data : xr.Dataset
        Terra NDSI dataset.
    myd_data : xr.Dataset
        Aqua NDSI dataset.
    mod_class_data : xr.Dataset
        Terra quality class dataset.
    myd_class_data : xr.Dataset
        Aqua quality class dataset.
    dem : np.ndarray
        Digital Elevation Model (lat, lon).
    nanmask : np.ndarray
        Boolean mask for invalid pixels.
    daysbefore : int
        Number of days before current in window.
    daysafter : int
        Number of days after current in window.
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
    save_pixel_counters: bool = False
) -> Tuple[xr.Dataset, dict]:
    """
    Process MODIS time series and save to Zarr format.
    
    This is the main processing entry point for cloud data. It applies the
    5-day moving window gap-filling algorithm with Terra/Aqua fusion.
    
    Parameters
    ----------
    mod_ds : xr.Dataset
        Terra (MOD10A1) NDSI dataset.
    myd_ds : xr.Dataset
        Aqua (MYD10A1) NDSI dataset.
    mod_class_ds : xr.Dataset
        Terra quality class dataset.
    myd_class_ds : xr.Dataset
        Aqua quality class dataset.
    dem_ds : xr.Dataset
        Digital Elevation Model dataset.
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
        
    Returns
    -------
    Tuple[xr.Dataset, dict]
        Processed NDSI dataset and counters dictionary.
    """
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
    daysbefore = 3
    daysafter = 2
    
    if verbose:
        print_section("Processing Configuration")
        print_config("Moving window", f"{daysbefore} days before, {daysafter} days after")
        print_config("Interpolation", interpolation_method)
        print_config("Spatial correction", spatial_correction_method)
    
    # Prepare DEM and nanmask
    dem, nanmask = _prepare_dem_data(dem_ds)
    
    if verbose:
        print_config("Data shape", f"{dem.shape[0]} x {dem.shape[1]} pixels")
        print_config("Invalid pixels (outside ROI)", f"{np.sum(nanmask):,}")
    
    # Transpose datasets for cloud data (lat, lon, time)
    if source == 'cloud':
        mod_ds = mod_ds.transpose('lat', 'lon', 'time')
        myd_ds = myd_ds.transpose('lat', 'lon', 'time')
        mod_class_ds = mod_class_ds.transpose('lat', 'lon', 'time')
        myd_class_ds = myd_class_ds.transpose('lat', 'lon', 'time')
    
    # Validate data
    if var_name not in mod_ds or var_name not in myd_ds:
        raise ValueError(f"Dataset does not contain variable '{var_name}'.")
    
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
    
    if verbose:
        print_config("Time range", f"{series[0].strftime('%Y-%m-%d')} to {series[-1].strftime('%Y-%m-%d')}")
        print_config("Days to process", f"{len(series) - daysbefore - daysafter:,}")
    
    # Standardize time format for efficient lookup
    mod_ds['time'] = mod_ds['time'].dt.strftime('%Y-%m-%d')
    myd_ds['time'] = myd_ds['time'].dt.strftime('%Y-%m-%d')
    mod_class_ds['time'] = mod_class_ds['time'].dt.strftime('%Y-%m-%d')
    myd_class_ds['time'] = myd_class_ds['time'].dt.strftime('%Y-%m-%d')
    
    # Process time series
    if verbose:
        print_info("Starting processing...")
    
    out_arr, out_dates, counters = process_files_array(
        series, movwind, currentday_ind,
        mod_ds, myd_ds, mod_class_ds, myd_class_ds,
        dem, nanmask, daysbefore, daysafter, var_name,
        interpolation_method=interpolation_method,
        spatial_correction_method=spatial_correction_method,
        verbose=verbose,
        save_pixel_counters=save_pixel_counters
    )
    
    # Create output dataset
    ds_out = xr.Dataset(
        {
            var_name: (("lat", "lon", "time"), out_arr)
        },
        coords={
            "lat": mod_ds["lat"],
            "lon": mod_ds["lon"],
            "time": out_dates
        },
        attrs={
            "processing_method": "SnowMapPy moving window gap-filling",
            "interpolation_method": interpolation_method,
            "window_days_before": daysbefore,
            "window_days_after": daysafter,
            "spatial_correction_method": spatial_correction_method
        }
    )
    
    # Save to Zarr with optimized compression
    if verbose:
        print_info(f"Saving to {output_zarr}/{file_name}.zarr...")
    
    save_as_zarr(ds_out, output_zarr, file_name)
    
    # Save counters to CSV if requested
    if save_pixel_counters and counters:
        counters_df = pd.DataFrame(counters)
        counters_csv_path = os.path.join(output_zarr, f"{file_name}_pixel_counters.csv")
        counters_df.to_csv(counters_csv_path, index=False)
        
        if verbose:
            print_info(f"Pixel counters saved to: {counters_csv_path}")
            
            # Print summary statistics
            total_spatial = sum(counters['spatial_filled_count'])
            total_temporal = sum(counters['temporal_filled_count'])
            avg_original_nan = sum(counters['original_nan_count']) / len(counters['original_nan_count'])
            
            print_config("Total spatial filled", f"{total_spatial:,} pixels")
            print_config("Total temporal filled", f"{total_temporal:,} pixels")
            print_config("Avg. original NaN/day", f"{avg_original_nan:,.0f} pixels")
    
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
    verbose: bool = True
) -> Tuple[xr.Dataset, dict]:
    """
    Complete cloud processing pipeline for MODIS NDSI data from Google Earth Engine.
    
    This is the main entry point for processing MODIS snow cover data. It handles:
    1. Loading data from Google Earth Engine
    2. Clipping to study area
    3. Gap-filling using 5-day moving window
    4. Terra/Aqua sensor fusion
    5. Elevation-based snow correction
    6. Temporal interpolation
    7. Saving results to Zarr format
    8. Saving pixel counters to CSV
    
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
        Name for output time series file. If None, defaults to
        '<shapefile_name>_NDSI' (e.g., 'study_area_NDSI').
    crs : str
        Coordinate reference system (default: 'EPSG:4326').
    save_original_data : bool
        Save original Terra/Aqua data before processing.
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
    ...     interpolation_method="linear",
    ...     spatial_correction_method="elevation_mean"
    ... )
    """
    # Default file_name to shapefile name + _NDSI
    if file_name is None:
        shapefile_basename = os.path.splitext(os.path.basename(shapefile_path))[0]
        file_name = f"{shapefile_basename}_NDSI"
    
    if verbose:
        print_banner()
        print_section("Processing Parameters")
        print_config("Study area", shapefile_path)
        print_config("Date range", f"{start_date} to {end_date}")
        print_config("Output", f"{output_path}/{file_name}.zarr")
        print()
    
    # Load data from Google Earth Engine
    if verbose:
        print_section("Loading data from Google Earth Engine")
    
    (ds_terra_value_clipped, ds_aqua_value_clipped,
     ds_terra_class_clipped, ds_aqua_class_clipped,
     ds_dem_clipped, roi_checker) = load_modis_cloud_data(
        project_name, shapefile_path, start_date, end_date, crs
    )
    
    # Save original data if requested
    if save_original_data:
        if verbose:
            print_info("Saving original data from Google Earth Engine...")
        ds_terra_value_clipped.to_zarr(
            os.path.join(output_path, f"{terra_file_name}.zarr"), mode="w"
        )
        ds_aqua_value_clipped.to_zarr(
            os.path.join(output_path, f"{aqua_file_name}.zarr"), mode="w"
        )
        ds_dem_clipped.to_zarr(
            os.path.join(output_path, f"{dem_file_name}.zarr"), mode="w"
        )
        ds_terra_class_clipped.to_zarr(
            os.path.join(output_path, f"{terra_file_name}_class.zarr"), mode="w"
        )
        ds_aqua_class_clipped.to_zarr(
            os.path.join(output_path, f"{aqua_file_name}_class.zarr"), mode="w"
        )
    
    # Process time series
    if verbose:
        print_section("Time Series Analysis")
    
    time_series, counters = modis_time_series_cloud(
        ds_terra_value_clipped, ds_aqua_value_clipped,
        ds_terra_class_clipped, ds_aqua_class_clipped,
        ds_dem_clipped, output_path, file_name,
        var_name='NDSI_Snow_Cover',
        source='cloud',
        interpolation_method=interpolation_method,
        spatial_correction_method=spatial_correction_method,
        verbose=verbose,
        save_pixel_counters=save_pixel_counters
    )
    
    if verbose:
        print_complete("Cloud processing pipeline completed successfully!")
    
    return time_series, counters