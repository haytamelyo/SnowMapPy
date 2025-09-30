import os
import zarr
import json
import shutil
import numcodecs
from numcodecs import Blosc
import numpy as np
import xarray as xr
import geopandas as gpd
import concurrent.futures
from affine import Affine

import os
import json
import shutil
import numpy as np
import xarray as xr
import concurrent.futures
from affine import Affine

# Use Zarr v3–compatible codecs via numcodecs.zarr3
from numcodecs.zarr3 import Zstd, Blosc, Zlib, BZ2, LZMA, LZ4


def optimal_combination(data, save_dir=None, vname=None, chunk_factors=None, compressors=None, sample_size=256):
    """Find optimal compression settings by testing different combinations on a data sample."""
    if save_dir is None:
        save_dir = os.getcwd()
    if vname is None:
        vname = 'NDSI'

    full_shape = data[vname].shape
    sample_shape = tuple(min(s, sample_size) for s in full_shape)

    def propose_chunk_sizes(shape):
        factors = chunk_factors or [4, 8, 16, 32]
        proposals = [tuple(max(1, s // f) for s in shape) for f in factors]
        return list(set(proposals))

    da_full = data[vname]
    ds_full = xr.Dataset({vname: da_full})
    sample_indices = {dim: slice(0, min(ds_full.sizes[dim], sample_size)) for dim in ds_full[vname].dims}
    ds_sample = ds_full.isel(**sample_indices)

    def test_compression(ds, zarr_path, compressor, chunks):
        encoding = {var: {'compressors': (compressor,), 'chunks': chunks} for var in ds.data_vars}
        ds.to_zarr(zarr_path, mode='w', encoding=encoding)
        size = 0
        for root, _, files in os.walk(zarr_path):
            for f in files:
                size += os.path.getsize(os.path.join(root, f))
        return size

    def find_best_compression(ds, compressors, chunk_sizes):
        best_params = (None, None, float('inf'))
        def worker(name, comp, chunks):
            path = os.path.join(save_dir, f'temp_{name}_{"-".join(map(str, chunks))}.zarr')
            try:
                sz = test_compression(ds, path, comp, chunks)
            finally:
                if os.path.isdir(path): shutil.rmtree(path)
            return name, chunks, sz

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as exe:
            futures = [exe.submit(worker, n, c, ch) for n, c in compressors.items() for ch in chunk_sizes]
            for fut in concurrent.futures.as_completed(futures):
                name, chunks, sz = fut.result()
                if sz < best_params[2]:
                    best_params = (name, chunks, sz)
        return best_params

    chunk_sizes = propose_chunk_sizes(sample_shape)
    if compressors is None:
        compressors = {
            'zlib': Zlib(level=5),
            'bz2': BZ2(level=9),
            'lzma': LZMA(preset=9),
            'zstd': Zstd(level=5),
            'lz4': LZ4(),
        }
        for cname in ['zstd','lz4','blosclz','zlib','lz4hc']:
            compressors[f'blosc_{cname}_cl5_sh1'] = Blosc(cname=cname, clevel=5, shuffle=1)

    best_name, best_chunks, _ = find_best_compression(ds_sample, compressors, chunk_sizes)
    params = {'compressor': best_name, 'chunk_size': best_chunks}
    pfile = os.path.join(save_dir, 'oparams.json')
    with open(pfile, 'w') as f:
        json.dump(params, f)
    return pfile


def save_as_zarr(ds: xr.Dataset, output_folder: str, file_name: str, params_file: str = None) -> str:
    """Save xarray Dataset as optimized Zarr store."""
    if not output_folder:
        raise ValueError("Output folder must be provided.")
    os.makedirs(output_folder, exist_ok=True)
    
    zarr_path = os.path.join(output_folder, f"{file_name}.zarr")
    
    if params_file and os.path.exists(params_file):
        with open(params_file, 'r') as f:
            params = json.load(f)
        
        compressor_name = params.get('compressor', 'zstd')
        chunk_size = params.get('chunk_size', (64, 64, 1))
        
        # Available compressors
        compressors = {
            'zlib': Zlib(level=5),
            'bz2': BZ2(level=9),
            'lzma': LZMA(preset=9),
            'zstd': Zstd(level=5),
            'lz4': LZ4(),
        }
        for cname in ['zstd','lz4','blosclz','zlib','lz4hc']:
            compressors[f'blosc_{cname}_cl5_sh1'] = Blosc(cname=cname, clevel=5, shuffle=1)
        
        compressor = compressors.get(compressor_name, Zstd(level=5))
        
        encoding = {}
        for var in ds.data_vars:
            encoding[var] = {
                'compressors': (compressor,),
                'chunks': chunk_size
            }
        
        ds.to_zarr(zarr_path, mode='w', encoding=encoding)
    else:
        # Default compression if no optimization params
        encoding = {}
        for var in ds.data_vars:
            encoding[var] = {
                'compressors': (Zstd(level=5),),
                'chunks': (64, 64, 1)
            }
        ds.to_zarr(zarr_path, mode='w', encoding=encoding)
    
    return zarr_path


def basic_save_as_zarr(NDSI, save_dir, file_name, DateSve):
    """Basic save function for NDSI data."""
    ds = xr.Dataset(
        data_vars={'NDSI': (('lat', 'lon'), NDSI)},
        coords={'time': [DateSve]}
    )
    return save_as_zarr(ds, save_dir, file_name)


def load_or_create_nan_array(directory, filename, shape):
    """Load data from zarr file or create nan array if file doesn't exist."""
    file_path = os.path.join(directory, filename)
    if os.path.exists(file_path):
        return zarr.open(file_path, mode='r')['NDSI'][:]
    else:
        return np.full(shape, np.nan)


def load_dem_and_nanmask(demdir):
    """Load DEM data and create nan mask."""
    dem = zarr.open(demdir, mode='r')['elevation'][:]
    nanmask = np.isnan(dem)
    return dem, nanmask


def load_shapefile(shp_path):
    """Load shapefile using geopandas."""
    return gpd.read_file(shp_path)