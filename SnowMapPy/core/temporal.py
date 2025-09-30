import numpy as np
from scipy.interpolate import griddata
from joblib import Parallel, delayed


def interpolate_pixel_griddata(flat_data, combined_mask, time_indices, i):
    """Interpolate time series data for a single pixel using griddata."""
    known_points = time_indices[~combined_mask[i, :]]
    known_values = flat_data[i, ~combined_mask[i, :]]
    if len(known_points) > 0:
        return griddata(known_points, known_values, time_indices, method='nearest', fill_value='extrapolate')
    return flat_data[i, :]


def vectorized_interpolation_griddata_parallel(data, nanmask, n_jobs=-1):
    """Interpolate time series data using parallel griddata processing."""
    time_indices = np.arange(data.shape[2])
    
    # Reshape to 2D for processing
    flat_data = data.reshape(-1, data.shape[2])
    
    # Create combined mask for NaN values and nanmask
    combined_mask = np.isnan(flat_data) | nanmask.reshape(-1, 1)
    
    # Parallel interpolation over pixels
    interpolated_flat_data = Parallel(n_jobs=n_jobs)(
        delayed(interpolate_pixel_griddata)(flat_data, combined_mask, time_indices, i)
        for i in range(flat_data.shape[0])
    )
    
    # Reshape back to original dimensions
    return np.array(interpolated_flat_data).reshape(data.shape)