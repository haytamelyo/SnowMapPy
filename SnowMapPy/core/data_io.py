"""
Data I/O Operations
===================

Read and write MODIS NDSI datasets with optimized compression.

Uses Zarr format with ZSTD compression for efficient storage and
fast random access to large snow cover datasets.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import os
import zarr
import json
import time
import tempfile
import shutil
import numpy as np
import xarray as xr
import geopandas as gpd
from typing import Optional, Tuple, Dict, Any, List

from numcodecs.zarr3 import Zstd

try:
    from numcodecs import LZ4, Blosc, Zlib
    EXTRA_CODECS_AVAILABLE = True
except ImportError:
    EXTRA_CODECS_AVAILABLE = False

DEFAULT_COMPRESSOR = Zstd(level=3)
DEFAULT_CHUNKS = (128, 128, 32)


def save_as_zarr(
    ds: xr.Dataset,
    output_folder: str,
    file_name: str,
    chunks: Optional[Tuple[int, int, int]] = None,
    compression_level: int = 3,
    dtype: Optional[str] = 'float16',
    params_file: Optional[str] = None  # Kept for backward compatibility, ignored
) -> str:
    """
    Save xarray Dataset as optimized Zarr store.
    
    Uses ZSTD compression which provides excellent compression ratios with
    fast read/write speeds. The chunk size is optimized for typical MODIS
    access patterns (spatial queries with some temporal slicing).
    
    MEMORY OPTIMIZATION: Set dtype='float16' (default) to reduce storage and memory by 50%.
    Float16 supports NaN values and is sufficient for NDSI data (0-100 range).
    
    NOTE: Only data variables are converted to the specified dtype. Coordinate
    variables (lat, lon, time) remain in their original precision (typically
    float64) to maintain spatial/temporal accuracy.
    
    Parameters
    ----------
    ds : xr.Dataset
        Dataset to save.
    output_folder : str
        Directory to save the Zarr store.
    file_name : str
        Name for the Zarr store (without .zarr extension).
    chunks : tuple of int, optional
        Chunk sizes as (lat, lon, time). Default is (128, 128, 32).
        Larger spatial chunks improve compression; larger time chunks
        improve time-series queries.
    compression_level : int, optional
        ZSTD compression level (1-22). Default is 3.
        - Level 1-3: Fast compression, good for large datasets
        - Level 4-6: Balanced compression/speed
        - Level 7+: Slower, diminishing returns on ratio
    dtype : str, optional
        Output data type for data variables. Options: 'float16' (default),
        'float32', 'float64'.
        - 'float16': 50% memory/storage savings, preserves NaN (recommended)
        - 'float32': Standard precision
        - 'float64': Full precision
        
        NOTE: Integer types (int16, uint8, etc.) are NOT supported because
        NDSI data requires NaN representation for missing values.
    params_file : str, optional
        Deprecated parameter, kept for backward compatibility. Ignored.
        
    Returns
    -------
    str
        Path to the saved Zarr store.
        
    Raises
    ------
    ValueError
        If dtype is not one of 'float16', 'float32', 'float64'.
        Integer types are explicitly rejected.
        
    Examples
    --------
    >>> import xarray as xr
    >>> from SnowMapPy.core.data_io import save_as_zarr
    >>> 
    >>> ds = xr.Dataset({"ndsi": (("lat", "lon", "time"), data)})
    >>> path = save_as_zarr(ds, "/output", "modis_ndsi")  # Uses float16 by default
    """
    if not output_folder:
        raise ValueError("Output folder must be provided.")
    
    os.makedirs(output_folder, exist_ok=True)
    zarr_path = os.path.join(output_folder, f"{file_name}.zarr")
    
    # Validate and apply dtype conversion for data variables only
    valid_dtypes = {'float16': np.float16, 'float32': np.float32, 'float64': np.float64}
    invalid_dtypes = ['int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64']
    
    if dtype is not None:
        dtype_lower = dtype.lower().strip()
        
        # Check for integer types and reject them
        if dtype_lower in invalid_dtypes:
            raise ValueError(
                f"Invalid dtype '{dtype}'. Integer types are not supported because:\\n"
                f"  - NDSI data requires NaN representation for missing values\\n"
                f"  - Integer types cannot represent NaN\\n"
                f"  - Minimum supported dtype is 'float16' (sufficient for NDSI range 0-100)\\n"
                f"\\nValid options: {', '.join(valid_dtypes.keys())}"
            )
        
        if dtype_lower not in valid_dtypes:
            raise ValueError(
                f"Unsupported dtype '{dtype}'.\\n"
                f"Valid options: {', '.join(valid_dtypes.keys())}\\n"
                f"Recommended: 'float16' (50% memory savings, sufficient for NDSI 0-100 range)"
            )
        
        target_dtype = valid_dtypes[dtype_lower]
        
        # Convert only DATA variables to the target dtype
        # Coordinates (lat, lon, time) remain in their original precision
        ds_converted = ds.copy()
        for var in ds.data_vars:
            if ds[var].dtype != target_dtype:
                ds_converted[var] = ds[var].astype(target_dtype)
        ds = ds_converted
    
    # Determine chunk sizes
    if chunks is None:
        # Adaptive chunking based on data size
        chunks = _calculate_optimal_chunks(ds)
    
    # Create compressor
    compressor = Zstd(level=compression_level)
    
    # Build encoding for all data variables
    encoding = {}
    for var in ds.data_vars:
        var_shape = ds[var].shape
        # Adjust chunks if larger than data dimensions
        var_chunks = tuple(min(c, s) for c, s in zip(chunks, var_shape))
        encoding[var] = {
            'compressors': (compressor,),
            'chunks': var_chunks
        }
    
    # Save to Zarr
    ds.to_zarr(zarr_path, mode='w', encoding=encoding)
    
    return zarr_path


def find_optimal_zarr_params(
    ds: xr.Dataset,
    sample_fraction: float = 0.1,
    compression_levels: List[int] = None,
    chunk_factors: List[Tuple[int, int, int]] = None,
    target_metric: str = 'balanced',
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Find optimal Zarr compression and chunking parameters for a dataset.
    
    Tests multiple combinations of compression algorithms/levels and chunk sizes
    to find the best balance between file size and write speed.
    
    Parameters
    ----------
    ds : xr.Dataset
        Dataset to optimize. Only a sample is used for testing.
    sample_fraction : float
        Fraction of time steps to use for testing (0.0-1.0). Default 0.1 (10%).
        Higher values give more accurate results but take longer.
    compression_levels : list of int, optional
        ZSTD compression levels to test. Default [1, 3, 5, 9].
        Higher levels = better compression, slower write.
    chunk_factors : list of tuple, optional
        Chunk size multipliers for (lat, lon, time). Default tests various sizes.
    target_metric : str
        Optimization target: 'size' (smallest file), 'speed' (fastest write),
        or 'balanced' (best size-speed trade-off). Default 'balanced'.
    verbose : bool
        Print progress and results.
        
    Returns
    -------
    dict
        Optimal parameters:
        {
            'compression_level': int,
            'chunks': tuple,
            'estimated_size_mb': float,
            'write_speed_mb_s': float,
            'all_results': list  # All tested combinations
        }
    """
    if compression_levels is None:
        compression_levels = [1, 3, 5, 9]
    
    first_var = list(ds.data_vars)[0]
    shape = ds[first_var].shape
    
    if len(shape) != 3:
        if verbose:
            print("Optimization only supports 3D datasets. Using default parameters.")
        return {
            'compression_level': 3,
            'chunks': DEFAULT_CHUNKS,
            'estimated_size_mb': None,
            'write_speed_mb_s': None,
            'all_results': []
        }
    
    lat_size, lon_size, time_size = shape
    
    if chunk_factors is None:
        chunk_factors = [
            (lat_size, lon_size, min(32, time_size)),
            (lat_size, lon_size, min(64, time_size)),
            (lat_size, lon_size, min(128, time_size)),
            (min(256, lat_size), min(256, lon_size), min(32, time_size)),
            (min(128, lat_size), min(128, lon_size), min(64, time_size)),
        ]
    
    sample_time = max(1, int(time_size * sample_fraction))
    sample_time = min(sample_time, time_size, 50)
    ds_sample = ds.isel(time=slice(0, sample_time))
    
    if verbose:
        print(f"Testing Zarr optimization with {sample_time}/{time_size} time steps...")
        print(f"Testing {len(compression_levels)} compression levels x {len(chunk_factors)} chunk configs\n")
    
    results = []
    temp_dir = tempfile.mkdtemp(prefix='zarr_opt_')
    
    try:
        for comp_level in compression_levels:
            for chunks in chunk_factors:
                valid_chunks = (
                    min(chunks[0], lat_size),
                    min(chunks[1], lon_size),
                    min(chunks[2], sample_time)
                )
                
                test_path = os.path.join(temp_dir, f"test_c{comp_level}_ch{valid_chunks[2]}")
                
                compressor = Zstd(level=comp_level)
                encoding = {}
                for var in ds_sample.data_vars:
                    var_shape = ds_sample[var].shape
                    var_chunks = tuple(min(c, s) for c, s in zip(valid_chunks, var_shape))
                    encoding[var] = {
                        'compressors': (compressor,),
                        'chunks': var_chunks
                    }
                
                start_time = time.time()
                ds_sample.to_zarr(test_path, mode='w', encoding=encoding)
                write_time = time.time() - start_time
                
                total_size = 0
                for root, dirs, files in os.walk(test_path):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))
                size_mb = total_size / (1024 * 1024)
                
                scale_factor = time_size / sample_time
                estimated_full_size = size_mb * scale_factor
                write_speed = size_mb / write_time if write_time > 0 else 0
                
                results.append({
                    'compression_level': comp_level,
                    'chunks': valid_chunks,
                    'sample_size_mb': size_mb,
                    'estimated_full_size_mb': estimated_full_size,
                    'write_time_s': write_time,
                    'write_speed_mb_s': write_speed
                })
                
                shutil.rmtree(test_path, ignore_errors=True)
                
                if verbose:
                    print(f"  ZSTD-{comp_level}, chunks={valid_chunks}: "
                          f"{estimated_full_size:.1f}MB est., {write_speed:.1f}MB/s")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    if not results:
        return {
            'compression_level': 3,
            'chunks': DEFAULT_CHUNKS,
            'estimated_size_mb': None,
            'write_speed_mb_s': None,
            'all_results': []
        }
    
    if target_metric == 'size':
        best = min(results, key=lambda x: x['estimated_full_size_mb'])
    elif target_metric == 'speed':
        best = max(results, key=lambda x: x['write_speed_mb_s'])
    else:
        max_size = max(r['estimated_full_size_mb'] for r in results)
        max_speed = max(r['write_speed_mb_s'] for r in results)
        
        for r in results:
            size_score = 1 - (r['estimated_full_size_mb'] / max_size) if max_size > 0 else 0
            speed_score = r['write_speed_mb_s'] / max_speed if max_speed > 0 else 0
            r['balanced_score'] = 0.6 * size_score + 0.4 * speed_score
        
        best = max(results, key=lambda x: x['balanced_score'])
    
    if verbose:
        print(f"\nOptimal parameters ({target_metric} optimization):")
        print(f"  Compression: ZSTD level {best['compression_level']}")
        print(f"  Chunks: {best['chunks']}")
        print(f"  Estimated size: {best['estimated_full_size_mb']:.1f} MB")
        print(f"  Write speed: {best['write_speed_mb_s']:.1f} MB/s")
    
    return {
        'compression_level': best['compression_level'],
        'chunks': best['chunks'],
        'estimated_size_mb': best['estimated_full_size_mb'],
        'write_speed_mb_s': best['write_speed_mb_s'],
        'all_results': results
    }


def save_as_zarr_optimized(
    ds: xr.Dataset,
    output_folder: str,
    file_name: str,
    auto_optimize: bool = True,
    optimization_target: str = 'balanced',
    sample_fraction: float = 0.1,
    dtype: Optional[str] = 'float16',
    verbose: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """
    Save xarray Dataset as Zarr with automatic optimization of parameters.
    
    Parameters
    ----------
    ds : xr.Dataset
        Dataset to save.
    output_folder : str
        Directory for output.
    file_name : str
        Output file name (without .zarr).
    auto_optimize : bool
        If True, find optimal compression/chunking. If False, use defaults.
    optimization_target : str
        'size', 'speed', or 'balanced'. Only used if auto_optimize=True.
    sample_fraction : float
        Fraction of data to use for optimization testing.
    dtype : str, optional
        Output dtype ('float16', 'float32', 'float64').
    verbose : bool
        Print progress.
        
    Returns
    -------
    tuple
        (zarr_path, optimization_results)
    """
    if auto_optimize:
        if verbose:
            print("Finding optimal Zarr parameters...")
        opt_results = find_optimal_zarr_params(
            ds,
            sample_fraction=sample_fraction,
            target_metric=optimization_target,
            verbose=verbose
        )
        compression_level = opt_results['compression_level']
        chunks = opt_results['chunks']
    else:
        opt_results = {'compression_level': 3, 'chunks': None, 'all_results': []}
        compression_level = 3
        chunks = None
    
    zarr_path = save_as_zarr(
        ds=ds,
        output_folder=output_folder,
        file_name=file_name,
        chunks=chunks,
        compression_level=compression_level,
        dtype=dtype
    )
    
    return zarr_path, opt_results


def _calculate_optimal_chunks(ds: xr.Dataset) -> Tuple[int, int, int]:
    """
    Calculate optimal chunk sizes based on dataset dimensions.
    
    Aims for chunks of approximately 1-4 MB for efficient I/O.
    """
    # Get first data variable to determine shape
    first_var = list(ds.data_vars)[0]
    shape = ds[first_var].shape
    
    if len(shape) == 3:
        lat_size, lon_size, time_size = shape
        
        # Target chunk size in elements (assuming float64 = 8 bytes)
        # Target ~2MB chunks: 2MB / 8 bytes = 262144 elements
        target_elements = 262144
        
        # Prioritize spatial chunking for MODIS data
        # Time dimension gets smaller chunks for efficient temporal slicing
        if lat_size * lon_size <= target_elements:
            # Small spatial extent: use full spatial dims
            lat_chunk = lat_size
            lon_chunk = lon_size
            time_chunk = max(1, min(time_size, target_elements // (lat_size * lon_size)))
        else:
            # Larger spatial extent: balance spatial and temporal
            spatial_chunk = int(np.sqrt(target_elements / 32))  # Assume ~32 time steps
            lat_chunk = min(lat_size, max(64, spatial_chunk))
            lon_chunk = min(lon_size, max(64, spatial_chunk))
            time_chunk = min(time_size, 32)
        
        return (lat_chunk, lon_chunk, time_chunk)
    
    elif len(shape) == 2:
        # 2D data (e.g., DEM)
        lat_size, lon_size = shape
        chunk_size = int(np.sqrt(262144))  # ~512
        return (min(lat_size, chunk_size), min(lon_size, chunk_size))
    
    else:
        # Default fallback
        return DEFAULT_CHUNKS[:len(shape)]


def load_dem_and_nanmask(dem_data) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load DEM data and create NaN mask for invalid pixels.
    
    Parameters
    ----------
    dem_data : str or xr.Dataset
        Either a path to a Zarr store containing DEM data, or an xarray
        Dataset with 'elevation' variable.
        
    Returns
    -------
    dem : np.ndarray
        2D array of elevation values.
    nanmask : np.ndarray
        2D boolean array where True indicates invalid (NaN) pixels.
    """
    if isinstance(dem_data, str):
        # Load from Zarr path
        dem = zarr.open(dem_data, mode='r')['elevation'][:]
    elif isinstance(dem_data, xr.Dataset):
        # Extract from xarray Dataset
        dem_ds = dem_data
        
        # Handle time dimension if present (take first time step)
        if 'time' in dem_ds.dims:
            dem_ds = dem_ds.isel(time=0)
        
        # Ensure proper dimension order (lat, lon)
        if set(dem_ds.dims) == {'lat', 'lon'}:
            dem_ds = dem_ds.transpose('lat', 'lon')
        elif set(dem_ds.dims) == {'lon', 'lat'}:
            dem_ds = dem_ds.transpose('lat', 'lon')
            
        dem = dem_ds['elevation'].values
    else:
        raise TypeError(f"dem_data must be str or xr.Dataset, got {type(dem_data)}")
    
    # Ensure 2D
    if dem.ndim == 3:
        dem = dem[:, :, 0] if dem.shape[2] == 1 else dem[0, :, :]
    
    # Create NaN mask
    nanmask = np.isnan(dem)
    
    return dem.astype(np.float64), nanmask


def load_shapefile(shp_path: str) -> gpd.GeoDataFrame:
    """
    Load shapefile using geopandas.
    
    Parameters
    ----------
    shp_path : str
        Path to the shapefile.
        
    Returns
    -------
    gpd.GeoDataFrame
        Loaded shapefile data.
    """
    return gpd.read_file(shp_path)


def load_zarr_dataset(zarr_path: str) -> xr.Dataset:
    """
    Load a Zarr store as xarray Dataset.
    
    Parameters
    ----------
    zarr_path : str
        Path to the Zarr store.
        
    Returns
    -------
    xr.Dataset
        Loaded dataset.
    """
    return xr.open_zarr(zarr_path)


# Legacy function - kept for backward compatibility but deprecated
def optimal_combination(data, save_dir=None, vname=None, chunk_factors=None, 
                        compressors=None, sample_size=256):
    """
    .. deprecated::
        This function is deprecated and does nothing. ZSTD level 3 is now
        used by default, which provides excellent compression without the
        overhead of testing multiple combinations.
        
    This function previously tested multiple compression combinations to find
    the optimal one. However, this was found to be:
    1. Time-consuming (5-10 minutes of processing)
    2. Providing minimal improvement (<5% better compression)
    
    The function now returns None and prints a deprecation warning.
    """
    import warnings
    warnings.warn(
        "optimal_combination is deprecated and has no effect. "
        "ZSTD level 3 compression is now used by default, which provides "
        "excellent compression without the overhead of testing combinations.",
        DeprecationWarning,
        stacklevel=2
    )
    return None