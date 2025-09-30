"""
MODIS NDSI Cloud Processing

Cloud-based processing for MODIS NDSI data from Google Earth Engine.
Handles data loading, quality control, and temporal interpolation.
"""

import os
import ee
import geemap
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
import geopandas as gpd

try:
    from ..core.data_io import save_as_zarr
    from ..core.temporal import vectorized_interpolation_griddata_parallel
    from ..core.quality import get_invalid_modis_classes
    from ..core.utils import generate_time_series
    from .loader import load_modis_cloud_data
except ImportError:
    # Fallback for direct imports
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
    """Load DEM data and create nanmask for invalid pixels."""
    # Transpose and remove time dimension (elevation is static)
    dem_ds = dem_ds.transpose('lat', 'lon', 'time')
    dem_ds = dem_ds.isel(time=0)
    dem = dem_ds['elevation'].values
    nanmask = np.isnan(dem)
    return dem, nanmask


def load_or_create_nan_array(dataset, date, shape, var_name):
    """Load data for specific date or create NaN array if missing."""
    date = date.strftime('%Y-%m-%d')
    if date in dataset.time.values:
        return dataset.sel(time=date)[var_name].values
    else:
        return np.full(shape, np.nan)


def process_files_array(series, movwind, currentday_ind, mod_data, myd_data, mod_class_data, myd_class_data,
                          dem, nanmask, daysbefore, daysafter, var_name):
    """Process time series using moving window approach with quality control."""
    mod_arr = mod_data[var_name].values
    lat_dim, lon_dim, _ = mod_arr.shape
    n_processed = len(series) - daysbefore - daysafter
    out_arr = np.empty((lat_dim, lon_dim, n_processed), dtype=np.float64)
    out_dates = []

    for i in tqdm(range(daysbefore, len(series) - daysafter), desc="Processing Files"):
        
        if i == daysbefore:
            # Initialize moving window
            window_mod = np.array([load_or_create_nan_array(mod_data, series[i + j], (lat_dim, lon_dim), var_name) for j in movwind])
            window_myd = np.array([load_or_create_nan_array(myd_data, series[i + j], (lat_dim, lon_dim), var_name) for j in movwind])
            window_mod_class = np.array([load_or_create_nan_array(mod_class_data, series[i + j], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class') for j in movwind])
            window_myd_class = np.array([load_or_create_nan_array(myd_class_data, series[i + j], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class') for j in movwind])

            # Move time to last axis
            window_mod = np.moveaxis(window_mod, 0, -1)
            window_myd = np.moveaxis(window_myd, 0, -1)
            window_mod_class = np.moveaxis(window_mod_class, 0, -1)
            window_myd_class = np.moveaxis(window_myd_class, 0, -1)
        else:
            # Roll window forward
            window_mod = np.roll(window_mod, -1, axis=2)
            window_myd = np.roll(window_myd, -1, axis=2)
            window_mod_class = np.roll(window_mod_class, -1, axis=2)
            window_myd_class = np.roll(window_myd_class, -1, axis=2)

            window_mod[:, :, -1] = np.array(load_or_create_nan_array(mod_data, series[i + daysafter], (lat_dim, lon_dim), var_name))
            window_myd[:, :, -1] = np.array(load_or_create_nan_array(myd_data, series[i + daysafter], (lat_dim, lon_dim), var_name))
            window_mod_class[:, :, -1] = np.array(load_or_create_nan_array(mod_class_data, series[i + daysafter], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class'))
            window_myd_class[:, :, -1] = np.array(load_or_create_nan_array(myd_class_data, series[i + daysafter], (lat_dim, lon_dim), 'NDSI_Snow_Cover_Class'))
        
        # Apply DEM mask
        window_mod[nanmask, :] = np.nan
        window_myd[nanmask, :] = np.nan
        window_mod_class[nanmask, :] = np.nan
        window_myd_class[nanmask, :] = np.nan

        # Quality control using class data
        invalid_classes = get_invalid_modis_classes()
        MOD_class_invalid = np.isin(window_mod_class, invalid_classes)
        MYD_class_invalid = np.isin(window_myd_class, invalid_classes)
        
        window_mod[MOD_class_invalid] = np.nan
        window_myd[MYD_class_invalid] = np.nan
        
        # Merge Terra and Aqua data
        MERGEind = np.isnan(window_mod) & ~np.isnan(window_myd)
        NDSIFill_MERGE = np.where(MERGEind, window_myd, window_mod)

        NDSI_merge = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])

        # Elevation-based snow correction for high altitude areas
        cond1 = np.float64(dem > 1000)
        cond2 = np.float64((dem > 1000) & np.isnan(NDSI_merge))
        if (np.sum(cond2) / np.sum(cond1)) < 0.60:
            sc = (NDSI_merge == 100)
            meanZ = np.mean(dem[sc])
            if np.sum(sc) > 10:
                ind = (dem > meanZ) & np.isnan(NDSI_merge)
                NDSI_merge[ind] = 100
                print('Applied elevation-based snow cover correction')

        # Clean and interpolate
        NDSIFill_MERGE[NDSIFill_MERGE > 100] = np.nan
        NDSIFill_MERGE = vectorized_interpolation_griddata_parallel(NDSIFill_MERGE, nanmask)
        NDSIFill_MERGE = np.clip(NDSIFill_MERGE, 0, 100)

        NDSI = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])
        dem_ind = dem < 1000
        # NDSI[dem_ind] = 0  # Optional: set low elevation to no snow

        out_arr[:, :, i - daysbefore] = NDSI
        out_dates.append(series[i])

    return out_arr, out_dates


def modis_time_series_cloud(mod_ds, myd_ds, mod_class_ds, myd_class_ds, dem_ds, output_zarr, file_name, var_name='NDSI_Snow_Cover', source='cloud', oparams_file=None):
    """Process MODIS time series and save to Zarr format."""
    daysbefore = 3
    daysafter = 2

    dem, nanmask = load_dem_and_nanmask(dem_ds)

    # Transpose for cloud data
    if source == 'cloud':
        mod_ds = mod_ds.transpose('lat', 'lon', 'time')
        myd_ds = myd_ds.transpose('lat', 'lon', 'time')
        mod_class_ds = mod_class_ds.transpose('lat', 'lon', 'time')
        myd_class_ds = myd_class_ds.transpose('lat', 'lon', 'time')

    if var_name not in mod_ds or var_name not in myd_ds:
        raise ValueError("One of the datasets does not contain the 'NDSI' variable.")

    mod_data = mod_ds[var_name].values
    myd_data = myd_ds[var_name].values
    mod_class_data = mod_class_ds['NDSI_Snow_Cover_Class'].values
    myd_class_data = myd_class_ds['NDSI_Snow_Cover_Class'].values

    if mod_data.shape[:2] != myd_data.shape[:2]:
        raise ValueError("Terra and Aqua data do not have matching spatial dimensions.")

    series, movwind, currentday_ind = generate_time_series(mod_ds['time'].values, daysbefore, daysafter)

    # Standardize time format
    mod_ds['time'] = mod_ds['time'].dt.strftime('%Y-%m-%d')
    myd_ds['time'] = myd_ds['time'].dt.strftime('%Y-%m-%d')
    mod_class_ds['time'] = mod_class_ds['time'].dt.strftime('%Y-%m-%d')
    myd_class_ds['time'] = myd_class_ds['time'].dt.strftime('%Y-%m-%d')

    out_arr, out_dates = process_files_array(series, movwind, currentday_ind, mod_ds, myd_ds, mod_class_ds, myd_class_ds,
                                               dem, nanmask, daysbefore, daysafter, var_name)

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
    
    save_as_zarr(ds_out, output_zarr, file_name, params_file=oparams_file)
    return ds_out


def process_modis_ndsi_cloud(project_name, shapefile_path, start_date, end_date, output_path, file_name = "time_series_cloud",
                             crs="EPSG:4326", save_original_data=False, terra_file_name="MOD", aqua_file_name="MYD", dem_file_name="DEM"):
    """Complete cloud processing pipeline for MODIS NDSI data from Google Earth Engine."""
    
    # Load data from Google Earth Engine
    (ds_terra_value_clipped, ds_aqua_value_clipped, 
     ds_terra_class_clipped, ds_aqua_class_clipped, 
     ds_dem_clipped, roi_checker) = load_modis_cloud_data(
        project_name, shapefile_path, start_date, end_date, crs
    )

    dem = ds_dem_clipped['elevation'].values
    nanmask = np.sum(np.isnan(dem))
    
    # Save original data if requested
    if save_original_data == True:
        print("Saving original data from Google Earth Engine")
        ds_terra_value_clipped.to_zarr(output_path + '/' + f"{terra_file_name}.zarr", mode="w")
        ds_aqua_value_clipped.to_zarr(output_path + '/' + f"{aqua_file_name}.zarr", mode="w")
        ds_dem_clipped.to_zarr(output_path + '/' + f"{dem_file_name}.zarr", mode="w")
        ds_terra_class_clipped.to_zarr(output_path + '/' + f"{terra_file_name}_class.zarr", mode="w")
        ds_aqua_class_clipped.to_zarr(output_path + '/' + f"{aqua_file_name}_class.zarr", mode="w")

    print('Starting time series analysis and processing')
    time_serie = modis_time_series_cloud(
        ds_terra_value_clipped, ds_aqua_value_clipped, 
        ds_terra_class_clipped, ds_aqua_class_clipped, 
        ds_dem_clipped, output_path, file_name, 
        var_name='NDSI_Snow_Cover', source='cloud'
    )

    print("Cloud processing pipeline completed successfully.")
    return time_serie