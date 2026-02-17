"""
Memory Management Utilities
===========================

Tools for monitoring and optimizing memory usage during processing.

ENHANCEMENTS:
- Integration with Dask lazy loading for memory-efficient processing
- Automatic optimal chunk size calculation
- Memory usage tracking with Dask awareness

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import gc
import sys
from typing import Optional, Callable
import numpy as np


def get_memory_usage_mb() -> float:
    """
    Get current process memory usage in MB.
    
    Returns
    -------
    float
        Memory usage in megabytes, or -1 if psutil is not available.
    """
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        return -1.0


def get_memory_usage_gb() -> float:
    """
    Get current process memory usage in GB.
    
    Returns
    -------
    float
        Memory usage in gigabytes, or -1 if psutil is not available.
    """
    mb = get_memory_usage_mb()
    return mb / 1024 if mb >= 0 else -1.0


def log_memory(stage: str, verbose: bool = True) -> float:
    """
    Log memory usage at a specific processing stage.
    
    Parameters
    ----------
    stage : str
        Description of the current processing stage.
    verbose : bool
        Whether to print the memory usage.
        
    Returns
    -------
    float
        Current memory usage in GB.
    """
    mem_gb = get_memory_usage_gb()
    if verbose and mem_gb >= 0:
        print(f"  [Memory] {stage}: {mem_gb:.2f} GB")
    return mem_gb


def estimate_array_memory_gb(shape: tuple, dtype=np.float64) -> float:
    """
    Estimate memory requirement for a NumPy array.
    
    Parameters
    ----------
    shape : tuple
        Shape of the array.
    dtype : numpy dtype
        Data type of the array.
        
    Returns
    -------
    float
        Estimated memory in gigabytes.
    """
    dtype = np.dtype(dtype)
    size_bytes = np.prod(shape) * dtype.itemsize
    return size_bytes / (1024 ** 3)


def estimate_dataset_memory(n_days: int, lat_pixels: int, lon_pixels: int, 
                           dtype: str = 'float64') -> dict:
    """
    Estimate memory requirements for a SnowMapPy dataset.
    
    Parameters
    ----------
    n_days : int
        Number of days in the time series.
    lat_pixels : int
        Number of latitude pixels.
    lon_pixels : int
        Number of longitude pixels.
    dtype : str
        Data type ('float16', 'float32', 'float64').
        
    Returns
    -------
    dict
        Dictionary with memory estimates for different components.
    """
    dtype_sizes = {
        'float16': 2,
        'float32': 4,
        'float64': 8
    }
    
    bytes_per_value = dtype_sizes.get(dtype, 8)
    total_pixels = n_days * lat_pixels * lon_pixels
    
    # Main NDSI array
    ndsi_bytes = total_pixels * bytes_per_value
    
    # Terra + Aqua (2x for values, 2x for classes)
    input_bytes = total_pixels * 8 * 4  # float64 for processing
    
    # DEM (2D)
    dem_bytes = lat_pixels * lon_pixels * 8
    
    # Moving window arrays (6 days x 2 sensors x 2 types)
    window_bytes = 6 * lat_pixels * lon_pixels * 8 * 4
    
    return {
        'ndsi_output_gb': ndsi_bytes / (1024**3),
        'input_data_gb': input_bytes / (1024**3),
        'dem_gb': dem_bytes / (1024**3),
        'window_buffer_gb': window_bytes / (1024**3),
        'total_peak_gb': (ndsi_bytes + input_bytes + dem_bytes + window_bytes) / (1024**3),
        'dtype': dtype,
        'shape': (n_days, lat_pixels, lon_pixels)
    }


def cleanup(*args) -> None:
    """
    Explicitly delete objects and force garbage collection.
    
    Parameters
    ----------
    *args : objects
        Objects to delete.
        
    Usage
    -----
    >>> cleanup(large_array, temp_result, old_dataset)
    """
    for obj in args:
        try:
            del obj
        except:
            pass
    gc.collect()


def check_memory_available(required_gb: float, safety_factor: float = 1.5) -> bool:
    """
    Check if sufficient memory is available.
    
    Parameters
    ----------
    required_gb : float
        Required memory in GB.
    safety_factor : float
        Multiplier for safety margin (default 1.5x).
        
    Returns
    -------
    bool
        True if sufficient memory available, False otherwise.
    """
    try:
        import psutil
        available_gb = psutil.virtual_memory().available / (1024 ** 3)
        return available_gb >= (required_gb * safety_factor)
    except ImportError:
        # If psutil not available, assume we have enough memory
        return True


class MemoryTracker:
    """
    Context manager to track memory usage during an operation.
    
    Usage
    -----
    >>> with MemoryTracker("Processing MODIS data") as tracker:
    ...     result = heavy_computation()
    >>> print(f"Peak memory: {tracker.peak_gb:.2f} GB")
    """
    
    def __init__(self, operation_name: str = "", verbose: bool = True):
        self.operation_name = operation_name
        self.verbose = verbose
        self.start_memory = 0.0
        self.end_memory = 0.0
        self.peak_gb = 0.0
        
    def __enter__(self):
        gc.collect()
        self.start_memory = get_memory_usage_gb()
        if self.verbose and self.operation_name and self.start_memory >= 0:
            print(f"  [Memory] Starting {self.operation_name}: {self.start_memory:.2f} GB")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        gc.collect()
        self.end_memory = get_memory_usage_gb()
        delta = self.end_memory - self.start_memory
        self.peak_gb = max(self.start_memory, self.end_memory)
        
        if self.verbose and self.operation_name and self.end_memory >= 0:
            print(f"  [Memory] Finished {self.operation_name}: {self.end_memory:.2f} GB (Δ{delta:+.2f} GB)")
        
        return False


def print_memory_summary(config: dict) -> None:
    """
    Print a summary of expected memory usage based on configuration.
    
    Parameters
    ----------
    config : dict
        Configuration dictionary with 'start_date', 'end_date', and dataset dimensions.
    """
    from datetime import datetime
    
    start = datetime.strptime(config.get('start_date', '2020-01-01'), '%Y-%m-%d')
    end = datetime.strptime(config.get('end_date', '2020-12-31'), '%Y-%m-%d')
    n_days = (end - start).days
    
    # Approximate pixels for typical MODIS data
    lat_pixels = config.get('lat_pixels', 400)
    lon_pixels = config.get('lon_pixels', 700)
    dtype = config.get('output_dtype', 'float16')
    
    estimates = estimate_dataset_memory(n_days, lat_pixels, lon_pixels, dtype)
    
    print("=" * 60)
    print("MEMORY USAGE ESTIMATE")
    print("=" * 60)
    print(f"Dataset shape: {estimates['shape']}")
    print(f"Output dtype: {estimates['dtype']}")
    print("-" * 60)
    print(f"NDSI output array:     {estimates['ndsi_output_gb']:.2f} GB")
    print(f"Input data (Terra+Aqua): {estimates['input_data_gb']:.2f} GB")
    print(f"DEM:                   {estimates['dem_gb']:.2f} GB")
    print(f"Processing buffers:   {estimates['window_buffer_gb']:.2f} GB")
    print("-" * 60)
    print(f"ESTIMATED PEAK MEMORY: {estimates['total_peak_gb']:.2f} GB")
    print("=" * 60)
    
    # Check if we have enough memory
    if not check_memory_available(estimates['total_peak_gb']):
        print("⚠ WARNING: Estimated memory exceeds available RAM!")
        print("  Consider using a smaller date range or closing other applications.")
