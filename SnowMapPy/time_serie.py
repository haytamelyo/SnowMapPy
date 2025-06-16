import sys
import numpy as np
from tqdm import tqdm
from .data_io import load_dem_and_nanmask
from .data_io import load_or_create_nan_array, basic_save_as_zarr
from .temporal_interpolation import vectorized_interpolation_griddata_parallel
from .file_handling import extract_date, generate_file_lists, get_map_dimensions, generate_time_series


# Function to process files
def process_files(series, movwind, currentday_ind, dir_MOD, dir_MYD, outputdir, row_mod, col_mod, row_myd, col_myd, dem, nanmask, daysbefore, daysafter, file_name='MODIS_NDSI'):
    dem_ind = dem < 1000

    for i in tqdm(range(daysbefore, len(series) - daysafter), desc="Processing Files"):
        # sys.stdout.write(f"\rProcessing date: {series[i].strftime('%Y-%m-%d')}")
        sys.stdout.flush()

        if i == daysbefore:
            NDSIFill_MOD = np.array([load_or_create_nan_array(dir_MOD, f'MOD10A1_NDSI_SCA_UpperTensift_Brute_{series[i+j].strftime("%Y-%m-%d")}.zarr', (row_mod, col_mod)) for j in movwind])
            NDSIFill_MYD = np.array([load_or_create_nan_array(dir_MYD, f'MYD10A1_NDSI_SCA_UpperTensift_Brute_{series[i+j].strftime("%Y-%m-%d")}.zarr', (row_myd, col_myd)) for j in movwind])

            NDSIFill_MYD = np.moveaxis(NDSIFill_MYD, 0, -1)
            NDSIFill_MOD = np.moveaxis(NDSIFill_MOD, 0, -1)
        else:
            NDSIFill_MOD = np.roll(NDSIFill_MOD, -1, axis=2)
            NDSIFill_MYD = np.roll(NDSIFill_MYD, -1, axis=2)

            NDSIFill_MOD[:, :, -1] = np.array(load_or_create_nan_array(dir_MOD, f'MOD10A1_NDSI_SCA_UpperTensift_Brute_{series[i + daysafter].strftime("%Y-%m-%d")}.zarr', (row_mod, col_mod)))
            NDSIFill_MYD[:, :, -1] = np.array(load_or_create_nan_array(dir_MYD, f'MYD10A1_NDSI_SCA_UpperTensift_Brute_{series[i + daysafter].strftime("%Y-%m-%d")}.zarr', (row_myd, col_myd)))

        NDSIFill_MOD[nanmask, :] = np.nan
        NDSIFill_MYD[nanmask, :] = np.nan

        codvals = [200, 201, 211, 237, 239, 250, 254, 255]
        MODind = np.isin(NDSIFill_MOD, codvals)
        MYDind = np.isin(NDSIFill_MYD, codvals)
        MERGEind = (MODind == 1) & (MYDind == 0)
        NDSIFill_MERGE = np.where(MERGEind, NDSIFill_MYD, NDSIFill_MOD)

        NDSI_merge = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])

        cond1 = np.float64(dem > 1000)
        cond2 = np.float64((dem > 1000) & np.isin(NDSI_merge, codvals))

        if (np.sum(cond2) / np.sum(cond1)) < 0.60:
            sc = (NDSI_merge == 100)
            meanZ = np.mean(dem[sc])
            if np.sum(sc) > 10:
                ind = (dem > meanZ) & np.isin(NDSI_merge, codvals)
                NDSI_merge[ind] = 100
                print('I did it')
        
        NDSIFill_MERGE[NDSIFill_MERGE > 100] = np.nan

        NDSIFill_MERGE = vectorized_interpolation_griddata_parallel(NDSIFill_MERGE, nanmask)

        NDSIFill_MERGE = np.clip(NDSIFill_MERGE, 0, 100)

        NDSI = np.squeeze(NDSIFill_MERGE[:, :, currentday_ind])
        NDSI[dem_ind] = 0
        basic_save_as_zarr(NDSI, outputdir, file_name, series[i].strftime('%Y-%m-%d'))


# Main function to run the script
def modis_time_serie(terra_dir, aqua_dir, dem_dir, output_dir, file_name='MODIS_NDSI'):
    daysbefore = 3
    daysafter = 2

    dem, nanmask = load_dem_and_nanmask(dem_dir)

    MODfiles, MYDfiles = generate_file_lists(terra_dir, aqua_dir)

    row_mod, col_mod, row_myd, col_myd = get_map_dimensions(terra_dir, aqua_dir, MODfiles, MYDfiles)

    mod_dates = [extract_date(f) for f in MODfiles]

    series, movwind, currentday_ind = generate_time_series(mod_dates, daysbefore, daysafter)

    process_files(series, movwind, currentday_ind, terra_dir, aqua_dir, output_dir, row_mod, col_mod, row_myd, col_myd, dem, nanmask, daysbefore, daysafter, file_name='MODIS_NDSI')
