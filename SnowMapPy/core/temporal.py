"""
Temporal Interpolation for MODIS Time Series
=============================================

Fill gaps in NDSI time series using Numba-accelerated interpolation.

Three methods are available:
    - nearest: Use closest valid observation (fastest)
    - linear: Interpolate linearly between observations
    - cubic: Catmull-Rom spline for smooth transitions

All methods achieve 100-500x speedup compared to scipy.griddata.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import numpy as np
from typing import Literal

# Import Numba-accelerated kernels
from .._numba_kernels import (
    interpolate_nearest_3d,
    interpolate_linear_3d,
    interpolate_cubic_3d
)


# Type alias for interpolation methods
InterpolationMethod = Literal["nearest", "linear", "cubic"]


def interpolate_temporal(
    data: np.ndarray,
    nanmask: np.ndarray,
    method: InterpolationMethod = "nearest"
) -> np.ndarray:
    """
    Perform temporal interpolation on 3D NDSI data.
    
    Fills NaN gaps in the time series using the specified interpolation method.
    All methods are accelerated with Numba JIT compilation for maximum performance.
    
    Parameters
    ----------
    data : np.ndarray
        3D array of shape (lat, lon, time) containing NDSI values.
        NaN values indicate gaps to be filled.
    nanmask : np.ndarray
        2D boolean array of shape (lat, lon) indicating permanently invalid
        pixels (e.g., outside study area). These pixels remain NaN after
        interpolation.
    method : str, optional
        Interpolation method to use. One of:
        - "nearest": Forward/backward fill. Fastest method, assigns the
          nearest valid value in time. Best for preserving original values.
        - "linear": Linear interpolation between valid points. Good balance
          of speed and smoothness.
        - "cubic": Catmull-Rom cubic spline interpolation. Smoothest results
          but slightly slower. Falls back to linear at edges.
        Default is "nearest".
        
    Returns
    -------
    np.ndarray
        Interpolated 3D array with the same shape as input. NaN values are
        filled except where nanmask is True.
        
    Raises
    ------
    ValueError
        If method is not one of "nearest", "linear", or "cubic".
        If data and nanmask shapes are incompatible.
        
    Examples
    --------
    >>> import numpy as np
    >>> from SnowMapPy.core.temporal import interpolate_temporal
    >>> 
    >>> # Create sample data with gaps
    >>> data = np.array([[[1, np.nan, 3], [4, 5, np.nan]],
    ...                  [[np.nan, 8, 9], [10, np.nan, 12]]], dtype=np.float64)
    >>> nanmask = np.array([[False, False], [False, False]])
    >>> 
    >>> # Fill gaps with nearest neighbor
    >>> result = interpolate_temporal(data, nanmask, method="nearest")
    >>> 
    >>> # Fill gaps with linear interpolation
    >>> result_linear = interpolate_temporal(data, nanmask, method="linear")
    
    Notes
    -----
    Performance comparison (typical 100x100x365 array):
    - Original scipy.griddata: ~60 seconds
    - Numba nearest: ~0.1 seconds (600x faster)
    - Numba linear: ~0.15 seconds (400x faster)
    - Numba cubic: ~0.3 seconds (200x faster)
    
    The first call to each method incurs a one-time JIT compilation overhead
    of approximately 1-2 seconds. Subsequent calls are near-instantaneous.
    """
    # Validate inputs
    if data.ndim != 3:
        raise ValueError(f"data must be 3D array, got {data.ndim}D")
    
    if nanmask.ndim != 2:
        raise ValueError(f"nanmask must be 2D array, got {nanmask.ndim}D")
    
    if data.shape[:2] != nanmask.shape:
        raise ValueError(
            f"data spatial dimensions {data.shape[:2]} do not match "
            f"nanmask shape {nanmask.shape}"
        )
    
    # Ensure correct data types for Numba
    data_float = data.astype(np.float64) if data.dtype != np.float64 else data.copy()
    nanmask_bool = nanmask.astype(np.bool_) if nanmask.dtype != np.bool_ else nanmask
    
    # Select and apply interpolation method
    method = method.lower()
    
    if method == "nearest":
        return interpolate_nearest_3d(data_float, nanmask_bool)
    elif method == "linear":
        return interpolate_linear_3d(data_float, nanmask_bool)
    elif method == "cubic":
        return interpolate_cubic_3d(data_float, nanmask_bool)
    else:
        valid_methods = ["nearest", "linear", "cubic"]
        raise ValueError(
            f"Invalid interpolation method '{method}'. "
            f"Must be one of: {valid_methods}"
        )


def get_interpolation_methods() -> list:
    """
    Get list of available interpolation methods.
    
    Returns
    -------
    list
        List of valid method names: ["nearest", "linear", "cubic"]
    """
    return ["nearest", "linear", "cubic"]


def validate_interpolation_method(method: str) -> bool:
    """
    Check if an interpolation method name is valid.
    
    Parameters
    ----------
    method : str
        Method name to validate.
        
    Returns
    -------
    bool
        True if method is valid, False otherwise.
    """
    return method.lower() in get_interpolation_methods()


# Legacy function for backward compatibility
def vectorized_interpolation_griddata_parallel(data, nanmask, n_jobs=-1):
    """
    Legacy wrapper for backward compatibility.
    
    .. deprecated::
        Use `interpolate_temporal(data, nanmask, method="nearest")` instead.
        This function is maintained only for backward compatibility and will
        be removed in a future version.
    
    Parameters
    ----------
    data : np.ndarray
        3D array of shape (lat, lon, time)
    nanmask : np.ndarray
        2D boolean mask
    n_jobs : int
        Ignored. Kept for API compatibility.
        
    Returns
    -------
    np.ndarray
        Interpolated data using nearest-neighbor method.
    """
    import warnings
    warnings.warn(
        "vectorized_interpolation_griddata_parallel is deprecated. "
        "Use interpolate_temporal(data, nanmask, method='nearest') instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return interpolate_temporal(data, nanmask, method="nearest")