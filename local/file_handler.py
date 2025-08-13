import os
import zarr
import datetime
import pandas as pd


def extract_date(filename):
    """
    Extract date from filename.
    """
    date_str = filename.split('_')[-1].split('.')[0]
    
    return datetime.datetime.strptime(date_str, '%Y-%m-%d')


def generate_file_lists(dir_MOD, dir_MYD):
    """
    Generate list of files.
    """
    MOD_file_name = os.path.basename(os.path.normpath(dir_MOD))
    MYD_file_name = os.path.basename(os.path.normpath(dir_MYD))
    MODfiles = sorted([f for f in os.listdir(dir_MOD) if f.endswith('.zarr') and f.startswith(MOD_file_name)])
    MYDfiles = sorted([f for f in os.listdir(dir_MYD) if f.endswith('.zarr') and f.startswith(MYD_file_name)])
    
    return MODfiles, MYDfiles


def get_map_dimensions(dir_MOD, dir_MYD, MODfiles, MYDfiles):
    """
    Get map dimensions.
    """
    row_mod, col_mod = zarr.open(os.path.join(dir_MOD, MODfiles[0]), mode='r')['SCA'][:].shape
    row_myd, col_myd = zarr.open(os.path.join(dir_MYD, MYDfiles[0]), mode='r')['SCA'][:].shape

    if row_mod != row_myd or col_mod != col_myd:
        raise ValueError('MODIS files do not have the same dimensions')
    
    return row_mod, col_mod, row_myd, col_myd 