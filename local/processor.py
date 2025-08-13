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
    """
    Return data or a nan array.
    """
    # Convert date to string
    date = date.strftime('%Y-%m-%d')
    if date in dataset.time.values:
        return dataset.sel(time=date)[var_name].values
    else:
        return np.full(shape, np.nan)


def process_files_array(series, movwind, currentday_ind, mod_data, myd_data,
                          dem, nanmask, daysbefore, daysafter, var_name):
    """
    Process the time series and accumulate processed images into a single array.
    """
    mod_arr = mod_data[var_name].values
    lat_dim, lon_dim, _ = mod_arr.shape
    n_processed = len(series) - daysbefore - daysafter
    out_arr = np.empty((lat_dim, lon_dim, n_processed), dtype=np.float64)
    out_dates = []

    for i in tqdm(range(daysbefore, len(series) - daysafter), desc="Processing Files"):
        
        if i == daysbefore:
            # Extract the moving window with specific days
            window_mod = np.array([load_or_create_nan_array(mod_data, series[i + j], (lat_dim, lon_dim), var_name) for j in movwind])
            window_myd = np.array([load_or_create_nan_array(myd_data, series[i + j], (lat_dim, lon_dim), var_name) for j in movwind])

            # Move the time dimension to the last axis
            window_mod = np.moveaxis(window_mod, 0, -1)
            window_myd = np.moveaxis(window_myd, 0, -1)
        else:
            window_mod = np.roll(window_mod, -1, axis=2)
            window_myd = np.roll(window_myd, -1, axis=2)
            # Printing shape after rolling

            window_mod[:, :, -1] = np.array(load_or_create_nan_array(mod_data, series[i + daysafter], (lat_dim, lon_dim), var_name))
            window_myd[:, :, -1] = np.array(load_or_create_nan_array(myd_data, series[i + daysafter], (lat_dim, lon_dim), var_name))

        # Apply the DEM nanmask
        window_mod[nanmask, :] = np.nan
        window_myd[nanmask, :] = np.nan

        # Merge Aqua and Terra based on quality codes
        codvals = [200, 201, 211, 237, 239, 250, 254, 255]
        MODind = np.isin(window_mod, codvals)
        MYDind = np.isin(window_myd, codvals)
        MERGEind = (MODind == 1) & (MYDind == 0)
        NDSIFill_MERGE = np.where(MERGEind, window_myd, window_mod)

        # Select the current day slice from the moving window
        NDSI_merge = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])

        # Quality control adjustment based on DEM values and code distribution
        cond1 = np.float64(dem > 1000)
        cond2 = np.float64((dem > 1000) & np.isin(NDSI_merge, codvals))
        if (np.sum(cond2) / np.sum(cond1)) < 0.60:
            sc = (NDSI_merge == 100)
            meanZ = np.mean(dem[sc])
            if np.sum(sc) > 10:
                ind = (dem > meanZ) & np.isin(NDSI_merge, codvals)
                NDSI_merge[ind] = 100
                print('I did it')

        # Clean up values and perform spatial interpolation on missing data
        NDSIFill_MERGE[NDSIFill_MERGE > 100] = np.nan
        NDSIFill_MERGE = vectorized_interpolation_griddata_parallel(NDSIFill_MERGE, nanmask)
        NDSIFill_MERGE = np.clip(NDSIFill_MERGE, 0, 100)

        NDSI = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])
        dem_ind = dem < 1000
        NDSI[dem_ind] = 0

        # Accumulate the processed image and record the date label
        out_arr[:, :, i - daysbefore] = NDSI
        # out_dates.append(series[i].strftime('%Y-%m-%d'))
        out_dates.append(series[i])

    return out_arr, out_dates


def modis_time_series(mod_ds, myd_ds, dem_ds, output_zarr, file_name, var_name='NDSI', oparams_file=None):
    """
    Main function to run the processing and save all images in a single zarr dataset.
    """
    daysbefore = 3
    daysafter = 2

    # Load DEM and create nanmask
    dem, nanmask = load_dem_and_nanmask(dem_ds)

    # Verify that both datasets contain the variable 'NDSI'
    if var_name not in mod_ds or var_name not in myd_ds:
        raise ValueError("One of the datasets does not contain the 'NDSI' variable.")

    # Get the full timeseries arrays; expected shape is (lat, lon, time)
    mod_data = mod_ds[var_name].values
    myd_data = myd_ds[var_name].values

    # Check that spatial dimensions match between Terra and Aqua data
    if mod_data.shape[:2] != myd_data.shape[:2]:
        raise ValueError("Terra and Aqua data do not have matching spatial dimensions.")

    # Generate a continuous daily time series and moving window parameters
    series, movwind, currentday_ind, _ = generate_time_series(mod_ds['time'].values, daysbefore, daysafter)

    # Process and accumulate all processed images
    out_arr, out_dates = process_files_array(series, movwind, currentday_ind, mod_ds, myd_ds,
                                               dem, nanmask, daysbefore, daysafter, var_name)

    # Create an xarray Dataset to store the complete time series in a single zarr file
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
    
    # Save the dataset to a single zarr store
    save_as_zarr(ds_out, output_zarr, file_name, params_file=oparams_file)

    return ds_out 