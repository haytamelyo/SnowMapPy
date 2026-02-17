"""
Numba-Accelerated Kernels for MODIS NDSI Processing
====================================================

This module contains JIT-compiled functions using Numba for high-performance
snow cover data processing. These functions replace the slower scipy-based
implementations with parallel, compiled alternatives.

The kernels handle:
    - Temporal interpolation (nearest, linear, cubic)
    - Terra/Aqua data merging with quality control
    - Elevation-based snow correction
    - Data clipping and masking

Performance: 50-200x faster than pure Python/scipy equivalents.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 1.0.0
"""

import numpy as np
from numba import njit, prange


# MODIS NDSI quality flag values that indicate invalid/unreliable data.
# These come from the MODIS MOD10A1/MYD10A1 product documentation:
#   200 = missing data
#   201 = no decision
#   211 = night
#   237 = inland water
#   239 = ocean
#   250 = cloud
#   254 = detector saturated
INVALID_CLASSES = np.array([200, 201, 211, 237, 239, 250, 254], dtype=np.float64)


@njit(cache=True)
def is_invalid_class(value):
    """
    Check if a MODIS quality class value indicates invalid data.
    
    Compares against the standard MODIS invalid class codes.
    """
    for inv in INVALID_CLASSES:
        if value == inv:
            return True
    return False


# =============================================================================
# TEMPORAL INTERPOLATION
# =============================================================================

@njit(parallel=True, cache=True)
def interpolate_nearest_3d(data, nanmask):
    """
    Fill gaps in time series using backward-first nearest valid observation.
    
    For each missing value, FIRST searches backward in time (past days).
    Only if no valid value exists in the past, then searches forward (future days).
    This prioritizes past observations over future ones, matching the original
    SnowMapPy gap-filling behavior.
    
    Args:
        data: 3D array (lat, lon, time) with NaN gaps
        nanmask: 2D boolean mask for permanently invalid pixels
    
    Returns:
        Gap-filled 3D array
    """
    rows, cols, times = data.shape
    result = data.copy()
    
    for i in prange(rows):
        for j in range(cols):
            if nanmask[i, j]:
                continue
            
            for t in range(times):
                if np.isnan(result[i, j, t]):
                    fill_val = np.nan
                    
                    # FIRST: Search backward in time (past days have priority)
                    for offset in range(1, times):
                        t_back = t - offset
                        if t_back >= 0 and not np.isnan(data[i, j, t_back]):
                            fill_val = data[i, j, t_back]
                            break
                    
                    # ONLY if no past value found, search forward in time
                    if np.isnan(fill_val):
                        for offset in range(1, times):
                            t_fwd = t + offset
                            if t_fwd < times and not np.isnan(data[i, j, t_fwd]):
                                fill_val = data[i, j, t_fwd]
                                break
                    
                    result[i, j, t] = fill_val
    
    return result


@njit(parallel=True, cache=True)
def interpolate_linear_3d(data, nanmask):
    """
    Fill gaps using linear interpolation between valid observations.
    
    For each pixel, finds valid observations before and after each gap
    and linearly interpolates between them. Edges are filled with the
    nearest valid value.
    
    Args:
        data: 3D array (lat, lon, time) with NaN gaps
        nanmask: 2D boolean mask for permanently invalid pixels
    
    Returns:
        Gap-filled 3D array
    """
    rows, cols, times = data.shape
    result = data.copy()
    
    for i in prange(rows):
        for j in range(cols):
            if nanmask[i, j]:
                continue
            
            # Collect indices of valid observations
            valid_indices = []
            for t in range(times):
                if not np.isnan(result[i, j, t]):
                    valid_indices.append(t)
            
            if len(valid_indices) == 0:
                continue
            elif len(valid_indices) == 1:
                # Only one observation - use it everywhere
                val = result[i, j, valid_indices[0]]
                for t in range(times):
                    result[i, j, t] = val
                continue
            
            # Interpolate between consecutive valid points
            for k in range(len(valid_indices) - 1):
                t1 = valid_indices[k]
                t2 = valid_indices[k + 1]
                v1 = result[i, j, t1]
                v2 = result[i, j, t2]
                
                for t in range(t1 + 1, t2):
                    alpha = (t - t1) / (t2 - t1)
                    result[i, j, t] = v1 + alpha * (v2 - v1)
            
            # Extend edges with nearest value
            first_valid = valid_indices[0]
            last_valid = valid_indices[-1]
            
            for t in range(0, first_valid):
                result[i, j, t] = result[i, j, first_valid]
            
            for t in range(last_valid + 1, times):
                result[i, j, t] = result[i, j, last_valid]
    
    return result


@njit(parallel=True, cache=True)
def interpolate_cubic_3d(data, nanmask):
    """
    Fill gaps using Catmull-Rom cubic spline interpolation.
    
    Produces smoother results than linear interpolation by using
    four control points. Falls back to linear when fewer than
    4 valid observations are available.
    
    Args:
        data: 3D array (lat, lon, time) with NaN gaps
        nanmask: 2D boolean mask for permanently invalid pixels
    
    Returns:
        Gap-filled 3D array
    """
    rows, cols, times = data.shape
    result = data.copy()
    
    for i in prange(rows):
        for j in range(cols):
            if nanmask[i, j]:
                continue
            
            valid_indices = []
            valid_values = []
            for t in range(times):
                if not np.isnan(result[i, j, t]):
                    valid_indices.append(t)
                    valid_values.append(result[i, j, t])
            
            n_valid = len(valid_indices)
            
            if n_valid == 0:
                continue
            elif n_valid == 1:
                val = valid_values[0]
                for t in range(times):
                    result[i, j, t] = val
                continue
            elif n_valid < 4:
                # Not enough points for cubic - use linear
                for k in range(n_valid - 1):
                    t1 = valid_indices[k]
                    t2 = valid_indices[k + 1]
                    v1 = valid_values[k]
                    v2 = valid_values[k + 1]
                    
                    for t in range(t1 + 1, t2):
                        alpha = (t - t1) / (t2 - t1)
                        result[i, j, t] = v1 + alpha * (v2 - v1)
            else:
                # Catmull-Rom spline interpolation
                for k in range(n_valid - 1):
                    t1 = valid_indices[k]
                    t2 = valid_indices[k + 1]
                    
                    # Four control points for the spline
                    p0_idx = max(0, k - 1)
                    p1_idx = k
                    p2_idx = k + 1
                    p3_idx = min(n_valid - 1, k + 2)
                    
                    p0 = valid_values[p0_idx]
                    p1 = valid_values[p1_idx]
                    p2 = valid_values[p2_idx]
                    p3 = valid_values[p3_idx]
                    
                    for t in range(t1 + 1, t2):
                        u = (t - t1) / (t2 - t1)
                        u2 = u * u
                        u3 = u2 * u
                        
                        # Catmull-Rom basis
                        result[i, j, t] = 0.5 * (
                            (2 * p1) +
                            (-p0 + p2) * u +
                            (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 +
                            (-p0 + 3 * p1 - 3 * p2 + p3) * u3
                        )
            
            # Extend edges
            first_valid = valid_indices[0]
            last_valid = valid_indices[-1]
            
            for t in range(0, first_valid):
                result[i, j, t] = result[i, j, first_valid]
            
            for t in range(last_valid + 1, times):
                result[i, j, t] = result[i, j, last_valid]
    
    return result


# =============================================================================
# QUALITY CONTROL AND DATA MERGING
# =============================================================================

@njit(parallel=True, cache=True)
def apply_invalid_mask_3d(data, class_data, invalid_classes):
    """
    Mask out pixels with invalid quality flags.
    
    Sets NDSI values to NaN where the corresponding quality class
    indicates unreliable data (clouds, water, missing, etc.).
    
    Args:
        data: 3D NDSI values (lat, lon, time)
        class_data: 3D quality class values
        invalid_classes: 1D array of invalid class codes
    
    Returns:
        Masked data array
    """
    rows, cols, times = data.shape
    result = data.copy()
    n_invalid = len(invalid_classes)
    
    for i in prange(rows):
        for j in range(cols):
            for t in range(times):
                class_val = class_data[i, j, t]
                for k in range(n_invalid):
                    if class_val == invalid_classes[k]:
                        result[i, j, t] = np.nan
                        break
    
    return result


@njit(parallel=True, cache=True)
def merge_terra_aqua_3d(terra_data, aqua_data, terra_class, aqua_class, invalid_classes):
    """
    Combine Terra (MOD10A1) and Aqua (MYD10A1) observations.
    
    Uses Terra as the primary source and fills gaps with Aqua data
    where Terra is missing or has an invalid quality flag.
    
    Args:
        terra_data: 3D Terra NDSI values
        aqua_data: 3D Aqua NDSI values
        terra_class: 3D Terra quality classes
        aqua_class: 3D Aqua quality classes
        invalid_classes: 1D array of invalid class codes
    
    Returns:
        Merged data array
    """
    rows, cols, times = terra_data.shape
    result = np.empty_like(terra_data)
    n_invalid = len(invalid_classes)
    
    for i in prange(rows):
        for j in range(cols):
            for t in range(times):
                terra_val = terra_data[i, j, t]
                aqua_val = aqua_data[i, j, t]
                terra_cls = terra_class[i, j, t]
                aqua_cls = aqua_class[i, j, t]
                
                # Check if Terra is usable
                terra_invalid = np.isnan(terra_val)
                if not terra_invalid:
                    for k in range(n_invalid):
                        if terra_cls == invalid_classes[k]:
                            terra_invalid = True
                            break
                
                # Check if Aqua is usable
                aqua_invalid = np.isnan(aqua_val)
                if not aqua_invalid:
                    for k in range(n_invalid):
                        if aqua_cls == invalid_classes[k]:
                            aqua_invalid = True
                            break
                
                # Prefer Terra, fall back to Aqua
                if terra_invalid and not aqua_invalid:
                    result[i, j, t] = aqua_val
                elif terra_invalid and aqua_invalid:
                    result[i, j, t] = np.nan
                else:
                    result[i, j, t] = terra_val
    
    return result


# =============================================================================
# ELEVATION-BASED SNOW CORRECTION
# =============================================================================

@njit(parallel=True, cache=True)
def apply_elevation_snow_correction(ndsi_data, dem, threshold_elevation=1000.0,
                                     snow_threshold=100.0, max_gap_ratio=0.60):
    """
    Fill missing high-elevation pixels with snow cover.
    
    Based on the physical principle that if snow exists at lower elevations,
    it should also exist at higher elevations. For missing pixels above the
    mean elevation of observed snow, assigns 100% snow cover.
    
    Only applies when the gap ratio is below max_gap_ratio to avoid
    over-correction during heavy cloud cover.
    
    Args:
        ndsi_data: 2D NDSI values for current day
        dem: 2D elevation data (meters)
        threshold_elevation: Minimum elevation to consider (default 1000m)
        snow_threshold: Value indicating full snow cover (default 100)
        max_gap_ratio: Maximum acceptable gap ratio (default 0.60)
    
    Returns:
        Corrected NDSI data
    """
    rows, cols = ndsi_data.shape
    result = ndsi_data.copy()
    
    # Count gaps at high elevation
    high_elev_count = 0
    high_elev_gap_count = 0
    
    for i in range(rows):
        for j in range(cols):
            if dem[i, j] > threshold_elevation:
                high_elev_count += 1
                if np.isnan(result[i, j]):
                    high_elev_gap_count += 1
    
    if high_elev_count == 0:
        return result
    
    gap_ratio = high_elev_gap_count / high_elev_count
    if gap_ratio >= max_gap_ratio:
        return result
    
    # Find mean elevation of snowy pixels
    snow_elev_sum = 0.0
    snow_count = 0
    
    for i in range(rows):
        for j in range(cols):
            if result[i, j] == snow_threshold:
                snow_elev_sum += dem[i, j]
                snow_count += 1
    
    if snow_count <= 10:
        return result
    
    mean_snow_elevation = snow_elev_sum / snow_count
    
    # Fill gaps above mean snow elevation
    for i in prange(rows):
        for j in range(cols):
            if np.isnan(result[i, j]) and dem[i, j] > mean_snow_elevation:
                result[i, j] = snow_threshold
    
    return result


@njit(parallel=True, cache=True)
def apply_spatial_snow_correction(ndsi_data, dem, window_size=3, min_elevation=1000.0):
    """
    Fill missing pixels based on surrounding snow observations (NEW method).
    
    For each gap pixel ABOVE the minimum elevation threshold, examines the 
    surrounding window. If neighboring pixels have snow at lower elevations, 
    the gap pixel (being higher) likely also has snow.
    
    Args:
        ndsi_data: 2D NDSI values
        dem: 2D elevation data
        window_size: Size of neighborhood window (default 3x3)
        min_elevation: Minimum elevation to apply correction (default 1000m)
    
    Returns:
        Tuple of (Corrected NDSI data, count of pixels filled)
    """
    rows, cols = ndsi_data.shape
    result = ndsi_data.copy()
    half_window = window_size // 2
    filled_count = 0
    
    for i in prange(rows):
        for j in range(cols):
            if not np.isnan(result[i, j]):
                continue
            
            pixel_elev = dem[i, j]
            if np.isnan(pixel_elev):
                continue
            
            # Only apply correction above minimum elevation (e.g., 1000m)
            if pixel_elev < min_elevation:
                continue
            
            # Check surrounding pixels for snow
            snow_neighbors = 0
            snow_elev_sum = 0.0
            
            for di in range(-half_window, half_window + 1):
                for dj in range(-half_window, half_window + 1):
                    if di == 0 and dj == 0:
                        continue
                    
                    ni = i + di
                    nj = j + dj
                    
                    if ni < 0 or ni >= rows or nj < 0 or nj >= cols:
                        continue
                    
                    neighbor_val = ndsi_data[ni, nj]
                    neighbor_elev = dem[ni, nj]
                    
                    if neighbor_val == 100.0 and not np.isnan(neighbor_elev):
                        snow_neighbors += 1
                        snow_elev_sum += neighbor_elev
            
            # If neighbors have snow at lower elevation, fill with snow
            if snow_neighbors > 0:
                mean_snow_elev = snow_elev_sum / snow_neighbors
                if pixel_elev > mean_snow_elev:
                    result[i, j] = 100.0
                    filled_count += 1
    
    return result, filled_count


@njit(parallel=True, cache=True)
def apply_old_spatial_snow_correction(ndsi_data, dem, threshold_elevation=1000.0,
                                       snow_threshold=100.0, max_gap_ratio=0.60):
    """
    Fill missing high-elevation pixels with snow cover (OLD/original method).
    
    Based on the physical principle that if snow exists at lower elevations,
    it should also exist at higher elevations. For missing pixels above the
    mean elevation of observed snow, assigns 100% snow cover.
    
    Only applies when the gap ratio is below max_gap_ratio to avoid
    over-correction during heavy cloud cover.
    
    This is the ORIGINAL method from the backup package.
    
    Args:
        ndsi_data: 2D NDSI values for current day
        dem: 2D elevation data (meters)
        threshold_elevation: Minimum elevation to consider (default 1000m)
        snow_threshold: Value indicating full snow cover (default 100)
        max_gap_ratio: Maximum acceptable gap ratio (default 0.60)
    
    Returns:
        Tuple of (Corrected NDSI data, count of pixels filled)
    """
    rows, cols = ndsi_data.shape
    result = ndsi_data.copy()
    filled_count = 0
    
    # Count gaps at high elevation
    high_elev_count = 0
    high_elev_gap_count = 0
    
    for i in range(rows):
        for j in range(cols):
            if dem[i, j] > threshold_elevation:
                high_elev_count += 1
                if np.isnan(result[i, j]):
                    high_elev_gap_count += 1
    
    if high_elev_count == 0:
        return result, 0
    
    gap_ratio = high_elev_gap_count / high_elev_count
    if gap_ratio >= max_gap_ratio:
        return result, 0
    
    # Find mean elevation of snowy pixels
    snow_elev_sum = 0.0
    snow_count = 0
    
    for i in range(rows):
        for j in range(cols):
            if result[i, j] == snow_threshold:
                snow_elev_sum += dem[i, j]
                snow_count += 1
    
    if snow_count <= 10:
        return result, 0
    
    mean_snow_elevation = snow_elev_sum / snow_count
    
    # Fill gaps above mean snow elevation
    for i in prange(rows):
        for j in range(cols):
            if np.isnan(result[i, j]) and dem[i, j] > mean_snow_elevation:
                result[i, j] = snow_threshold
                filled_count += 1
    
    return result, filled_count


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

@njit(parallel=True, cache=True)
def clip_values_3d(data, min_val, max_val):
    """
    Constrain values to a valid range.
    
    NDSI values should be between 0 and 100.
    """
    rows, cols, times = data.shape
    result = data.copy()
    
    for i in prange(rows):
        for j in range(cols):
            for t in range(times):
                val = result[i, j, t]
                if not np.isnan(val):
                    if val < min_val:
                        result[i, j, t] = min_val
                    elif val > max_val:
                        result[i, j, t] = max_val
    
    return result


@njit(parallel=True, cache=True)
def apply_nanmask_3d(data, nanmask):
    """
    Apply a 2D spatial mask to all time steps.
    
    Pixels outside the region of interest are set to NaN.
    """
    rows, cols, times = data.shape
    result = data.copy()
    
    for i in prange(rows):
        for j in range(cols):
            if nanmask[i, j]:
                for t in range(times):
                    result[i, j, t] = np.nan
    
    return result


@njit(cache=True)
def set_values_above_threshold_to_nan(data, threshold):
    """
    Set values exceeding a threshold to NaN.
    
    Used to filter out invalid NDSI values > 100.
    """
    rows, cols, times = data.shape
    result = data.copy()
    
    for i in range(rows):
        for j in range(cols):
            for t in range(times):
                if result[i, j, t] > threshold:
                    result[i, j, t] = np.nan
    
    return result
