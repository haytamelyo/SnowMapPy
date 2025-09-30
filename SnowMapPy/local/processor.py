import os
import sys
import datetime
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
import matplotlib.pyplot as plt
from ..core.temporal import vectorized_interpolation_griddata_parallel
from ..core.data_io import save_as_zarr, load_dem_and_nanmask, load_shapefile
from ..core.utils import generate_time_series


def load_or_create_nan_array(dataset, date, shape, var_name):
    """Return data for date or NaN array if missing."""
    date = date.strftime('%Y-%m-%d')
    if date in dataset.time.values:
        return dataset.sel(time=date)[var_name].values
    else:
        return np.full(shape, np.nan)


def process_files_array(series, movwind, currentday_ind, mod_data, myd_data,
                          dem, nanmask, daysbefore, daysafter, var_name):
    """Process time series using moving window and accumulate results."""
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

            # Move time to last axis
            window_mod = np.moveaxis(window_mod, 0, -1)
            window_myd = np.moveaxis(window_myd, 0, -1)
        else:
            window_mod = np.roll(window_mod, -1, axis=2)
            window_myd = np.roll(window_myd, -1, axis=2)

            window_mod[:, :, -1] = np.array(load_or_create_nan_array(mod_data, series[i + daysafter], (lat_dim, lon_dim), var_name))
            window_myd[:, :, -1] = np.array(load_or_create_nan_array(myd_data, series[i + daysafter], (lat_dim, lon_dim), var_name))

        # Apply DEM mask
        window_mod[nanmask, :] = np.nan
        window_myd[nanmask, :] = np.nan

        # Merge Aqua and Terra based on quality codes
        codvals = [200, 201, 211, 237, 239, 250, 254, 255]
        MODind = np.isin(window_mod, codvals)
        MYDind = np.isin(window_myd, codvals)
        MERGEind = (MODind == 1) & (MYDind == 0)
        NDSIFill_MERGE = np.where(MERGEind, window_myd, window_mod)

        NDSI_merge = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])

        # Elevation-based quality adjustment
        cond1 = np.float64(dem > 1000)
        cond2 = np.float64((dem > 1000) & np.isin(NDSI_merge, codvals))
        if (np.sum(cond2) / np.sum(cond1)) < 0.60:
            sc = (NDSI_merge == 100)
            meanZ = np.mean(dem[sc])
            if np.sum(sc) > 10:
                ind = (dem > meanZ) & np.isin(NDSI_merge, codvals)
                NDSI_merge[ind] = 100
                print('Applied elevation correction')

        # Clean and interpolate
        NDSIFill_MERGE[NDSIFill_MERGE > 100] = np.nan
        NDSIFill_MERGE = vectorized_interpolation_griddata_parallel(NDSIFill_MERGE, nanmask)
        NDSIFill_MERGE = np.clip(NDSIFill_MERGE, 0, 100)

        NDSI = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])
        dem_ind = dem < 1000
        NDSI[dem_ind] = 0

        out_arr[:, :, i - daysbefore] = NDSI
        out_dates.append(series[i])

    return out_arr, out_dates


def modis_time_series(mod_ds, myd_ds, dem_ds, output_zarr, file_name, var_name='NDSI', oparams_file=None):
    """Process MODIS time series and save to zarr format."""
    daysbefore = 3
    daysafter = 2

    dem, nanmask = load_dem_and_nanmask(dem_ds)

    if var_name not in mod_ds or var_name not in myd_ds:
        raise ValueError("One of the datasets does not contain the 'NDSI' variable.")

    mod_data = mod_ds[var_name].values
    myd_data = myd_ds[var_name].values

    if mod_data.shape[:2] != myd_data.shape[:2]:
        raise ValueError("Terra and Aqua data do not have matching spatial dimensions.")

    series, movwind, currentday_ind, _ = generate_time_series(mod_ds['time'].values, daysbefore, daysafter)

    out_arr, out_dates = process_files_array(series, movwind, currentday_ind, mod_ds, myd_ds,
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