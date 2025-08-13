"""
MODIS NDSI Cloud Processing Module

This module provides comprehensive cloud-based processing for MODIS NDSI (Normalized 
Difference Snow Index) data from Google Earth Engine. It implements a complete pipeline
for downloading, quality control, and temporal processing of snow cover data.

The processing pipeline includes:
1. Data loading from Google Earth Engine
2. Quality control using NDSI_Snow_Cover_Class
3. Temporal interpolation for missing data
4. Merging of Terra and Aqua satellite data
5. Export to Zarr format for efficient storage

Key Functions:
    - process_modis_ndsi_cloud(): Main processing function for cloud data
    - modis_time_series_cloud(): Time series processing and interpolation
    - process_files_array(): Core processing algorithm with moving window

Author: SnowMapPy Team
License: MIT
"""

import os
import ee
import geemap
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
import geopandas as gpd

# Try relative imports first, fall back to absolute imports
try:
    from ..core.data_io import save_as_zarr
    from ..core.temporal import vectorized_interpolation_griddata_parallel
    from ..core.quality import get_invalid_modis_classes
    from ..core.utils import generate_time_series
    from .loader import load_modis_cloud_data
except ImportError:
    # Fall back to absolute imports
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(current_dir)
    sys.path.insert(0, package_dir)
    
    from core.data_io import save_as_zarr
    from core.temporal import vectorized_interpolation_griddata_parallel
    from core.quality import get_invalid_modis_classes
    from core.utils import generate_time_series
    from cloud.loader import load_modis_cloud_data


def load_dem_and_nanmask(dem_ds):
    """
    Load Digital Elevation Model (DEM) and generate nanmask for invalid pixels.
    
    This function processes the DEM dataset to extract elevation data and create
    a mask identifying pixels with invalid (NaN) elevation values. The DEM is
    used for elevation-based quality control and spatial interpolation.
    
    Args:
        dem_ds (xarray.Dataset): DEM dataset with elevation variable
        
    Returns:
        tuple: (dem_array, nanmask)
            - dem_array (numpy.ndarray): 2D array of elevation values
            - nanmask (numpy.ndarray): Boolean mask of NaN pixels
            
    Note:
        The DEM is transposed to match the spatial dimensions of MODIS data
        and the time dimension is removed since elevation is static.
    """
    # Transpose the DEM data to match MODIS spatial dimensions
    dem_ds = dem_ds.transpose('lat', 'lon', 'time')
    # Remove time dimension (elevation is static)
    dem_ds = dem_ds.isel(time=0)
    dem = dem_ds['elevation'].values
    nanmask = np.isnan(dem)
    return dem, nanmask


def load_or_create_nan_array(dataset, date, shape, var_name):
    """
    Load data for a specific date or create a NaN array if data is missing.
    
    This function handles missing temporal data by creating NaN arrays for dates
    where MODIS data is not available. This ensures consistent array dimensions
    throughout the processing pipeline.
    
    Args:
        dataset (xarray.Dataset): Dataset containing the variable
        date (datetime): Date to extract data for
        shape (tuple): Shape of the array (lat, lon)
        var_name (str): Name of the variable to extract
        
    Returns:
        numpy.ndarray: Data array for the specified date or NaN array if missing
    """
    # Convert date to string format for dataset selection
    date = date.strftime('%Y-%m-%d')
    if date in dataset.time.values:
        return dataset.sel(time=date)[var_name].values
    else:
        return np.full(shape, np.nan)


def process_files_array(series, movwind, currentday_ind, mod_data, myd_data, mod_class_data, myd_class_data,
                          dem, nanmask, daysbefore, daysafter, var_name):
    """
    Process time series data using a moving window approach with quality control.
    
    This is the core processing function that implements the moving window algorithm
    for temporal interpolation and quality control. It processes each day in the
    time series using surrounding days to fill missing data and apply quality filters.
    
    The algorithm:
    1. Creates a moving window of surrounding days
    2. Applies DEM-based masking
    3. Uses NDSI_Snow_Cover_Class for quality control
    4. Merges Terra and Aqua data
    5. Performs spatial interpolation
    6. Applies elevation-based corrections
    
    Args:
        series (pandas.DatetimeIndex): Complete time series dates
        movwind (range): Moving window indices relative to current day
        currentday_ind (int): Index of current day in moving window
        mod_data (xarray.Dataset): Terra satellite data
        myd_data (xarray.Dataset): Aqua satellite data
        mod_class_data (xarray.Dataset): Terra quality class data
        myd_class_data (xarray.Dataset): Aqua quality class data
        dem (numpy.ndarray): Digital elevation model
        nanmask (numpy.ndarray): Mask for invalid DEM pixels
        daysbefore (int): Number of days before current day in window
        daysafter (int): Number of days after current day in window
        var_name (str): Name of the variable to process
        
    Returns:
        tuple: (processed_array, processed_dates)
            - processed_array (numpy.ndarray): 3D array of processed data (lat, lon, time)
            - processed_dates (list): List of processed dates
            
    Note:
        The moving window approach ensures temporal consistency and allows for
        interpolation of missing data using spatial and temporal information.
    """
    mod_arr = mod_data[var_name].values
    lat_dim, lon_dim, _ = mod_arr.shape
    n_processed = len(series) - daysbefore - daysafter
    out_arr = np.empty((lat_dim, lon_dim, n_processed), dtype=np.float64)
    out_dates = []

    for i in tqdm(range(daysbefore, len(series) - daysafter), desc="Processing Files"):
        
        if i == daysbefore:
            # Initialize moving window with data from surrounding days
            window_mod = np.array([load_or_create_nan_array(mod_data, series[i + j], (lat_dim, lon_dim), var_name) for j in movwind])
            window_myd = np.array([load_or_create_nan_array(myd_data, series[i + j], (lat_dim, lon_dim), var_name) for j in movwind])
            window_mod_class = np.array([load_or_create_nan_array(mod_class_data, series[i + j], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class') for j in movwind])
            window_myd_class = np.array([load_or_create_nan_array(myd_class_data, series[i + j], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class') for j in movwind])

            # Move time dimension to last axis for processing
            window_mod = np.moveaxis(window_mod, 0, -1)
            window_myd = np.moveaxis(window_myd, 0, -1)
            window_mod_class = np.moveaxis(window_mod_class, 0, -1)
            window_myd_class = np.moveaxis(window_myd_class, 0, -1)
        else:
            # Roll window forward and add new day
            window_mod = np.roll(window_mod, -1, axis=2)
            window_myd = np.roll(window_myd, -1, axis=2)
            window_mod_class = np.roll(window_mod_class, -1, axis=2)
            window_myd_class = np.roll(window_myd_class, -1, axis=2)

            window_mod[:, :, -1] = np.array(load_or_create_nan_array(mod_data, series[i + daysafter], (lat_dim, lon_dim), var_name))
            window_myd[:, :, -1] = np.array(load_or_create_nan_array(myd_data, series[i + daysafter], (lat_dim, lon_dim), var_name))
            window_mod_class[:, :, -1] = np.array(load_or_create_nan_array(mod_class_data, series[i + daysafter], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class'))
            window_myd_class[:, :, -1] = np.array(load_or_create_nan_array(myd_class_data, series[i + daysafter], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class'))
        
        # Apply DEM-based masking (set invalid elevation pixels to NaN)
        window_mod[nanmask, :] = np.nan
        window_myd[nanmask, :] = np.nan
        window_mod_class[nanmask, :] = np.nan
        window_myd_class[nanmask, :] = np.nan

        # Quality control using NDSI_Snow_Cover_Class
        # Invalid classes from Google Earth Engine documentation:
        # 200 (Missing data), 201 (No decision), 211 (Night), 237 (Inland water), 
        # 239 (Ocean), 250 (Cloud), 254 (Detector saturated)
        invalid_classes = get_invalid_modis_classes()
        
        # Create masks for invalid class values
        MOD_class_invalid = np.isin(window_mod_class, invalid_classes)
        MYD_class_invalid = np.isin(window_myd_class, invalid_classes)
        
        # Apply quality masks to NDSI data
        window_mod[MOD_class_invalid] = np.nan
        window_myd[MYD_class_invalid] = np.nan
        
        # Merge Terra and Aqua data: prefer Aqua where Terra is invalid
        MERGEind = np.isnan(window_mod) & ~np.isnan(window_myd)
        NDSIFill_MERGE = np.where(MERGEind, window_myd, window_mod)

        # Select current day from moving window
        NDSI_merge = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])

        # Elevation-based quality control and snow cover adjustment
        cond1 = np.float64(dem > 1000)  # High elevation pixels
        cond2 = np.float64((dem > 1000) & np.isnan(NDSI_merge))  # High elevation with missing data
        if (np.sum(cond2) / np.sum(cond1)) < 0.60:  # If less than 60% of high elevation pixels are missing
            sc = (NDSI_merge == 100)  # Snow cover pixels
            meanZ = np.mean(dem[sc])  # Mean elevation of snow cover
            if np.sum(sc) > 10:  # If sufficient snow cover pixels exist
                ind = (dem > meanZ) & np.isnan(NDSI_merge)  # High elevation missing pixels
                NDSI_merge[ind] = 100  # Assume snow cover at high elevations
                print('Applied elevation-based snow cover correction')

        # Clean up values and perform spatial interpolation
        NDSIFill_MERGE[NDSIFill_MERGE > 100] = np.nan  # Remove invalid values
        NDSIFill_MERGE = vectorized_interpolation_griddata_parallel(NDSIFill_MERGE, nanmask)  # Spatial interpolation
        NDSIFill_MERGE = np.clip(NDSIFill_MERGE, 0, 100)  # Clip to valid range

        NDSI = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])
        dem_ind = dem < 1000  # Low elevation pixels
        # NDSI[dem_ind] = 0  # Optional: set low elevation to no snow

        # Store processed result and date
        out_arr[:, :, i - daysbefore] = NDSI
        out_dates.append(series[i])

    return out_arr, out_dates


def modis_time_series_cloud(mod_ds, myd_ds, mod_class_ds, myd_class_ds, dem_ds, output_zarr, file_name, var_name='NDSI_Snow_Cover', source='cloud', oparams_file=None):
    """
    Process MODIS time series data and save results to Zarr format.
    
    This function orchestrates the complete time series processing pipeline for
    cloud-based MODIS data. It handles data preparation, quality control,
    temporal interpolation, and export to efficient Zarr storage format.
    
    Args:
        mod_ds (xarray.Dataset): Terra satellite NDSI data
        myd_ds (xarray.Dataset): Aqua satellite NDSI data
        mod_class_ds (xarray.Dataset): Terra satellite quality class data
        myd_class_ds (xarray.Dataset): Aqua satellite quality class data
        dem_ds (xarray.Dataset): Digital elevation model data
        output_zarr (str): Output directory for Zarr files
        file_name (str): Base filename for output files
        var_name (str, optional): Variable name to process. Defaults to 'NDSI_Snow_Cover'
        source (str, optional): Data source identifier. Defaults to 'cloud'
        oparams_file (str, optional): Optional parameters file. Defaults to None
        
    Returns:
        xarray.Dataset: Processed time series dataset
        
    Raises:
        ValueError: If datasets don't contain required variables or have mismatched dimensions
        
    Note:
        The function creates a complete time series with quality control and
        temporal interpolation, suitable for snow cover analysis and modeling.
    """
    daysbefore = 3  # Days before current day for moving window
    daysafter = 2   # Days after current day for moving window

    # Load DEM and create nanmask for elevation-based filtering
    dem, nanmask = load_dem_and_nanmask(dem_ds)

    # Transpose datasets for cloud data to match expected dimensions
    if source == 'cloud':
        mod_ds = mod_ds.transpose('lat', 'lon', 'time')
        myd_ds = myd_ds.transpose('lat', 'lon', 'time')
        mod_class_ds = mod_class_ds.transpose('lat', 'lon', 'time')
        myd_class_ds = myd_class_ds.transpose('lat', 'lon', 'time')

    # Validate that required variables exist in datasets
    if var_name not in mod_ds or var_name not in myd_ds:
        raise ValueError("One of the datasets does not contain the 'NDSI' variable.")

    # Extract data arrays for processing
    mod_data = mod_ds[var_name].values
    myd_data = myd_ds[var_name].values
    mod_class_data = mod_class_ds['NDSI_Snow_Cover_Class'].values
    myd_class_data = myd_class_ds['NDSI_Snow_Cover_Class'].values

    # Validate spatial dimensions match between Terra and Aqua data
    if mod_data.shape[:2] != myd_data.shape[:2]:
        raise ValueError("Terra and Aqua data do not have matching spatial dimensions.")

    # Generate continuous daily time series and moving window parameters
    series, movwind, currentday_ind = generate_time_series(mod_ds['time'].values, daysbefore, daysafter)

    # Standardize time format to YYYY-MM-DD (remove time components)
    mod_ds['time'] = mod_ds['time'].dt.strftime('%Y-%m-%d')
    myd_ds['time'] = myd_ds['time'].dt.strftime('%Y-%m-%d')
    mod_class_ds['time'] = mod_class_ds['time'].dt.strftime('%Y-%m-%d')
    myd_class_ds['time'] = myd_class_ds['time'].dt.strftime('%Y-%m-%d')

    # Process time series using moving window approach
    out_arr, out_dates = process_files_array(series, movwind, currentday_ind, mod_ds, myd_ds, mod_class_ds, myd_class_ds,
                                               dem, nanmask, daysbefore, daysafter, var_name)

    # Create xarray Dataset for the complete processed time series
    ds_out = xr.Dataset(
        {
            var_name: (("lat", "lon", "time"), out_arr)
        },
        coords={
            "lat": mod_ds["lat"],
            "lon": mod_ds["lon"],
            "time": out_dates
        }
    )
    
    # Save processed dataset to Zarr format for efficient storage
    save_as_zarr(ds_out, output_zarr, file_name, params_file=oparams_file)

    return ds_out


def process_modis_ndsi_cloud(project_name, shapefile_path, start_date, end_date, output_path, file_name = "time_series_cloud",
                             crs="EPSG:4326", save_original_data=False, terra_file_name="MOD", aqua_file_name="MYD", dem_file_name="DEM"):
    """
    Complete cloud processing pipeline for MODIS NDSI data from Google Earth Engine.
    
    This is the main entry point for cloud-based MODIS NDSI processing. It handles
    the complete workflow from data download to final processed time series:
    
    1. Authenticate and connect to Google Earth Engine
    2. Load MODIS NDSI data for specified region and time period
    3. Apply quality control and temporal processing
    4. Save results in efficient Zarr format
    5. Optionally save original data for reference
    
    Args:
        project_name (str): Google Earth Engine project name
        shapefile_path (str): Path to shapefile defining region of interest
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        output_path (str): Directory to save output files
        file_name (str, optional): Base filename for output. Defaults to "time_series_cloud"
        crs (str, optional): Coordinate reference system. Defaults to "EPSG:4326"
        save_original_data (bool, optional): Whether to save original GEE data. Defaults to False
        terra_file_name (str, optional): Filename for Terra data. Defaults to "MOD"
        aqua_file_name (str, optional): Filename for Aqua data. Defaults to "MYD"
        dem_file_name (str, optional): Filename for DEM data. Defaults to "DEM"
        
    Returns:
        xarray.Dataset: Processed time series dataset
        
    Example:
        >>> result = process_modis_ndsi_cloud(
        ...     project_name="my-gee-project",
        ...     shapefile_path="roi.shp",
        ...     start_date="2023-01-01",
        ...     end_date="2023-01-31",
        ...     output_path="output/",
        ...     file_name="snow_cover_jan2023"
        ... )
        
    Note:
        This function requires Google Earth Engine authentication and appropriate
        permissions for the specified project. The processing time depends on
        the size of the region and time period.
    """
    # Load MODIS data from Google Earth Engine
    (ds_terra_value_clipped, ds_aqua_value_clipped, 
     ds_terra_class_clipped, ds_aqua_class_clipped, 
     ds_dem_clipped, roi_checker) = load_modis_cloud_data(
        project_name, shapefile_path, start_date, end_date, crs
    )

    # Extract DEM statistics for quality assessment
    dem = ds_dem_clipped['elevation'].values
    nanmask = np.sum(np.isnan(dem))
    
    # Save original data if requested (useful for debugging and reference)
    if save_original_data == True:
        print("Saving original data from Google Earth Engine")
        ds_terra_value_clipped.to_zarr(output_path + '/' + f"{terra_file_name}.zarr", mode="w")
        ds_aqua_value_clipped.to_zarr(output_path + '/' + f"{aqua_file_name}.zarr", mode="w")
        ds_dem_clipped.to_zarr(output_path + '/' + f"{dem_file_name}.zarr", mode="w")
        ds_terra_class_clipped.to_zarr(output_path + '/' + f"{terra_file_name}_class.zarr", mode="w")
        ds_aqua_class_clipped.to_zarr(output_path + '/' + f"{aqua_file_name}_class.zarr", mode="w")

    # Process time series with quality control and interpolation
    print('Starting time series analysis and processing')
    time_serie = modis_time_series_cloud(
        ds_terra_value_clipped, ds_aqua_value_clipped, 
        ds_terra_class_clipped, ds_aqua_class_clipped, 
        ds_dem_clipped, output_path, file_name, 
        var_name='NDSI_Snow_Cover', source='cloud'
    )

    print("Cloud processing pipeline completed successfully.")
    return time_serie 