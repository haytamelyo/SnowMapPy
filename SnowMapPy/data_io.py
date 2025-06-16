import os
import zarr
import json
import numcodecs
import numpy as np
import xarray as xr
import geopandas as gpd
import concurrent.futures
from affine import Affine

# Function to propose chunk sizes
def optimal_combination(data, save_dir=None, vname=None, chunk_factors=None, compressors=None):
    if save_dir is None:
        save_dir = os.getcwd()

    if vname is None:
        vname = 'data'

    def propose_chunk_sizes(shape):
        if chunk_factors is None:
            factors = [2, 4, 8, 16, 32, 64]
        else:
            factors = chunk_factors
        
        proposals = []
        for factor in factors:
            chunks = tuple(max(1, s // factor) for s in shape)
            proposals.append(chunks)
        
        return list(set(proposals))

    def test_compression(ds, zarr_path, compressor, chunks):

        encoding = {var: {'compressor': compressor, 'chunks': chunks} for var in ds.data_vars}
        
        ds.to_zarr(zarr_path, mode='w', encoding=encoding)
        
        zarr_size = sum(os.path.getsize(os.path.join(root, file)) 
                        for root, _, files in os.walk(zarr_path) 
                        for file in files)
        
        return zarr_size

    def find_best_compression(ds, compressors, chunk_sizes):
        best_compressor = None
        best_chunk_size = None
        min_file_size = float('inf')

        def test_compression_combination(compressor_name, compressor, chunk_size):
            temp_zarr_path = os.path.join(save_dir, f'temp_{compressor_name}_chunks_{"-".join(map(str, chunk_size))}.zarr')
            zarr_size = test_compression(ds, temp_zarr_path, compressor, chunk_size)

            if os.path.exists(temp_zarr_path):
                import shutil
                shutil.rmtree(temp_zarr_path)

            return compressor_name, chunk_size, zarr_size

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(test_compression_combination, compressor_name, compressor, chunk_size)
                for compressor_name, compressor in compressors.items()
                for chunk_size in chunk_sizes
            ]

            for future in concurrent.futures.as_completed(futures):
                compressor_name, chunk_size, zarr_size = future.result()
                if zarr_size < min_file_size:
                    min_file_size = zarr_size
                    best_compressor = compressor_name
                    best_chunk_size = chunk_size

        return best_compressor, best_chunk_size, min_file_size

    chunk_sizes = propose_chunk_sizes(data.shape)

    if compressors is None:
        compressors = {
            'zlib': numcodecs.Zlib(level=5),
            'bz2': numcodecs.BZ2(level=9),
            'lzma': numcodecs.LZMA(preset=9),
            'zstd': numcodecs.Zstd(level=5),
            'lz4': numcodecs.LZ4(),
        }
        
        blosc_compressors = ['zstd', 'lz4', 'blosclz', 'zlib', 'lz4hc']
        for cname in blosc_compressors:
            for clevel in range(1, 10):
                for shuffle in range(0, 3):
                    compressor_name = f'blosc_{cname}_clevel_{clevel}_shuffle_{shuffle}'
                    compressors[compressor_name] = zarr.Blosc(cname=cname, clevel=clevel, shuffle=shuffle)

    da = xr.DataArray(data, dims=[f'dim_{i}' for i in range(data.ndim)])
    ds = xr.Dataset({vname: da})

    best_compressor, best_chunk_size, _ = find_best_compression(ds, compressors, chunk_sizes)

    best_params = {
        'compressor': best_compressor,
        'chunk_size': best_chunk_size
    }

    params_file = os.path.join(save_dir, 'oparams.json')
    with open(params_file, 'w') as f:
        json.dump(best_params, f)
        # Close the file
        f.close()
    
    return params_file


# Function to save data as Zarr with optimal compression
def save_as_zarr(data, save_dir, params_file=None, coords=None, dims=None, vname=None, name=None, attrs=None, split_attrs=False, save_attrs=True):
    if not save_dir:
        raise ValueError('Directory to save data must be provided.')

    if vname is None:
        vname = 'data'

    if name is None:
        name = 'data'

    if dims is None:
        dims = [f'dim_{i}' for i in range(data.ndim)]

    if params_file is None or not os.path.exists(params_file):
        if params_file is None:
            print(f'No params file provided for {name}.')
            inp = input('Do you want to run the optimal combination algorithm (1) or continue with the default combination (2): ')
        
        elif not os.path.exists(params_file):
            print(f'No params file provided for {name}.')
            inp = input('The oparams file does not exist. Do you want to run the optimal combination algorithm (1) or continue with the default combination (2): ')
        
        if inp == '1':
            print('Running the optimal combination algorithm... This may take a while!')
            # going back one folder behind from the save_dir
            oparams_save = os.path.dirname(save_dir)
            params_file = optimal_combination(data, oparams_save)
        
        elif inp == '2':
            default_params = {
                'compressor': 'zstd',
                'chunk_size': data.shape
            }
            params_file = os.path.join(save_dir, 'default_params.json')
            with open(params_file, 'w') as f:
                json.dump(default_params, f)

    da = xr.DataArray(data, coords=coords, dims=dims, name=vname)

    ds = xr.Dataset({vname: da})

    if attrs is not None and save_attrs:
        attrs = process_attrs(attrs)
        ds.attrs.update(attrs)

    with open(params_file, 'r') as f:
        best_params = json.load(f)
        # Close the file
        f.close()
    
    best_compressor_name = best_params['compressor']
    best_chunk_size = tuple(best_params['chunk_size'])

    compressors = {
        'zlib': numcodecs.Zlib(level=5),
        'bz2': numcodecs.BZ2(level=9),
        'lzma': numcodecs.LZMA(preset=9),
        'zstd': numcodecs.Zstd(level=5),
        'lz4': numcodecs.LZ4(),
    }

    blosc_compressors = ['zstd', 'lz4', 'blosclz', 'zlib', 'lz4hc']
    
    for cname in blosc_compressors:
        for clevel in range(1, 10):
            for shuffle in range(0, 3):
                compressor_name = f'blosc_{cname}_clevel_{clevel}_shuffle_{shuffle}'
                compressors[compressor_name] = zarr.Blosc(cname=cname, clevel=clevel, shuffle=shuffle)

    best_compressor = compressors[best_compressor_name]

    best_zarr_path = os.path.join(save_dir, f'{name}.zarr')
    best_encoding = {var: {'compressor': best_compressor, 'chunks': best_chunk_size} for var in ds.data_vars}
    
    if split_attrs and save_attrs:
        ds_data = ds.copy()
        ds_data.attrs = {}
        
        for var in ds_data.variables:
            ds_data[var].attrs = {}
        
        ds_data.to_zarr(best_zarr_path, mode='w', encoding=best_encoding)
        attrs_file = os.path.join(save_dir, 'attrs.zarr')
        ds_attrs = xr.Dataset(attrs)
        ds_attrs.to_zarr(attrs_file, mode='w')

        return params_file
    
    else:
        ds.to_zarr(best_zarr_path, mode='w', encoding=best_encoding)
        
        return params_file


# Function to process attributes
def process_attrs(attrs):
    processed_attrs = {}
    
    for key, value in attrs.items():
    
        if isinstance(value, Affine):
            processed_attrs[key] = str(value.to_gdal())
    
        elif isinstance(value, tuple):
            processed_attrs[key] = str(value)
    
        else:
            processed_attrs[key] = value
    
    return processed_attrs


# Function to save the NDSI as Zarr
def basic_save_as_zarr(NDSI, save_dir, file_name, DateSve):
    da = xr.DataArray(NDSI, dims=['y', 'x'], name='NDSI') # Create DataArray for NDSI
    ds = xr.Dataset({'NDSI': da}) # Create Dataset
    zarr_name = file_name + DateSve + '.zarr' # Define the name of the Zarr store
    zarr_path = os.path.join(save_dir, zarr_name) # Define the full path for the Zarr store
    ds.to_zarr(zarr_path, mode='w') # Save to Zarr with compression


# Function to load or create a NaN array if the file does not exist
def load_or_create_nan_array(directory, filename, shape):
    try:
        return zarr.open(os.path.join(directory, filename), mode='r')['SCA'][:]
    
    except:
        return np.full(shape, np.nan)


# Function to load DEM and generate nanmask
def load_dem_and_nanmask(demdir):
    dem = zarr.open(os.path.join(demdir, 'DEM.zarr'), mode='r')['DEM_BV'][:]
    nanmask = np.isnan(dem)
    return dem, nanmask


# Load shapefile function for ROI
def load_shapefile(shp_path):
    os.environ['SHAPE_RESTORE_SHX'] = 'YES'
    return gpd.read_file(shp_path)

