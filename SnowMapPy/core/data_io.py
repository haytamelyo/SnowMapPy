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
import numpy as np
import xarray as xr
import geopandas as gpd
from typing import Optional, Tuple, Dict, Any

# Use Zarr v3–compatible codecs via numcodecs.zarr3
from numcodecs.zarr3 import Zstd


# Default compression settings - ZSTD level 3 offers excellent balance
# of compression ratio and speed
DEFAULT_COMPRESSOR = Zstd(level=3)
DEFAULT_CHUNKS = (128, 128, 32)  # Optimized for spatial-temporal access patterns


def save_as_zarr(
    ds: xr.Dataset,
    output_folder: str,
    file_name: str,
    chunks: Optional[Tuple[int, int, int]] = None,
    compression_level: int = 3,
    params_file: Optional[str] = None  # Kept for backward compatibility, ignored
) -> str:
    """
    Save xarray Dataset as optimized Zarr store.
    
    Uses ZSTD compression which provides excellent compression ratios with
    fast read/write speeds. The chunk size is optimized for typical MODIS
    access patterns (spatial queries with some temporal slicing).
    
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
    params_file : str, optional
        Deprecated parameter, kept for backward compatibility. Ignored.
        
    Returns
    -------
    str
        Path to the saved Zarr store.
        
    Examples
    --------
    >>> import xarray as xr
    >>> from SnowMapPy.core.data_io import save_as_zarr
    >>> 
    >>> ds = xr.Dataset({"ndsi": (("lat", "lon", "time"), data)})
    >>> path = save_as_zarr(ds, "/output", "modis_ndsi")
    """
    if not output_folder:
        raise ValueError("Output folder must be provided.")
    
    os.makedirs(output_folder, exist_ok=True)
    zarr_path = os.path.join(output_folder, f"{file_name}.zarr")
    
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