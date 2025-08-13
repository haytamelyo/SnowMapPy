"""
MODIS NDSI Quality Control Module

This module provides comprehensive quality control functions for MODIS NDSI (Normalized 
Difference Snow Index) data processing. It implements class-based filtering using 
NDSI_Snow_Cover_Class values to identify and mask invalid pixels.

The quality control is based on Google Earth Engine's MODIS NDSI_Snow_Cover_Class 
documentation, which categorizes pixels into different classes including valid snow 
cover data and various types of invalid data (clouds, water bodies, missing data, etc.).

Key Functions:
    - get_invalid_modis_classes(): Returns list of invalid class values
    - create_modis_class_mask(): Creates boolean mask for invalid pixels
    - apply_modis_quality_mask(): Applies quality mask to NDSI data
    - validate_modis_class(): Validates individual class values

Author: SnowMapPy Team
License: MIT
"""

import numpy as np


def get_valid_modis_classes():
    """
    Get valid MODIS NDSI_Snow_Cover_Class values.
    
    These are the class values that represent valid snow cover data:
    - 1: Snow
    - 2: No snow  
    - 3: Water
    
    Returns:
        list: List of valid MODIS class values
    """
    return [1, 2, 3]  # snow, no snow, water


def get_invalid_modis_classes():
    """
    Get invalid MODIS NDSI_Snow_Cover_Class values that should be masked out.
    
    These class values represent various types of invalid or unusable data:
    - 200: Missing data
    - 201: No decision (insufficient data for classification)
    - 211: Night (no solar illumination)
    - 237: Inland water
    - 239: Ocean
    - 250: Cloud
    - 254: Detector saturated
    
    Returns:
        list: List of invalid MODIS class values to be masked
    """
    return [200, 201, 211, 237, 239, 250, 254]


def validate_modis_class(class_value):
    """
    Validate if a MODIS class value represents valid snow cover data.
    
    Args:
        class_value (int): MODIS NDSI_Snow_Cover_Class value to validate
        
    Returns:
        bool: True if the class value represents valid data, False if invalid
        
    Example:
        >>> validate_modis_class(1)
        True
        >>> validate_modis_class(250)
        False
    """
    valid_classes = get_valid_modis_classes()
    return class_value in valid_classes


def create_modis_class_mask(class_data, invalid_classes=None):
    """
    Create a boolean mask identifying invalid MODIS class values.
    
    This function creates a mask where True indicates pixels with invalid class
    values that should be excluded from analysis.
    
    Args:
        class_data (numpy.ndarray): Array of MODIS NDSI_Snow_Cover_Class values
        invalid_classes (list, optional): List of invalid class values to mask.
            If None, uses the default list from get_invalid_modis_classes()
        
    Returns:
        numpy.ndarray: Boolean mask where True indicates invalid pixels
        
    Example:
        >>> class_data = np.array([[1, 250], [2, 200]])
        >>> mask = create_modis_class_mask(class_data)
        >>> print(mask)
        [[False  True]
         [False  True]]
    """
    if invalid_classes is None:
        invalid_classes = get_invalid_modis_classes()
    
    return np.isin(class_data, invalid_classes)


def apply_modis_quality_mask(value_data, class_data, invalid_classes=None):
    """
    Apply quality control mask to MODIS NDSI value data.
    
    This function uses class data to identify invalid pixels in the NDSI value
    data and sets them to NaN. This ensures that only high-quality snow cover
    data is used for analysis.
    
    Args:
        value_data (numpy.ndarray): MODIS NDSI_Snow_Cover values (0-100)
        class_data (numpy.ndarray): MODIS NDSI_Snow_Cover_Class values
        invalid_classes (list, optional): List of invalid class values to mask.
            If None, uses the default list from get_invalid_modis_classes()
        
    Returns:
        numpy.ndarray: NDSI value data with invalid pixels set to NaN
        
    Example:
        >>> values = np.array([[50, 75], [25, 100]])
        >>> classes = np.array([[1, 250], [2, 200]])
        >>> masked = apply_modis_quality_mask(values, classes)
        >>> print(masked)
        [[50. nan]
         [25. nan]]
    """
    if invalid_classes is None:
        invalid_classes = get_invalid_modis_classes()
    
    # Create mask for invalid classes
    invalid_mask = np.isin(class_data, invalid_classes)
    
    # Apply mask to value data (set invalid pixels to NaN)
    masked_data = value_data.copy()
    masked_data[invalid_mask] = np.nan
    
    return masked_data 