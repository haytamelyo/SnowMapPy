"""
MODIS Quality Control
=====================

Filter unreliable pixels using MODIS snow cover classification.

The MODIS MOD10A1/MYD10A1 products include quality flags that identify
clouds, water, night pixels, and other conditions where snow detection
is unreliable. This module provides utilities for masking these pixels.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import numpy as np


def get_valid_modis_classes():
    """Return valid MODIS NDSI_Snow_Cover_Class values."""
    return [1, 2, 3]  # snow, no snow, water


def get_invalid_modis_classes():
    """Return invalid MODIS class values that should be masked out."""
    return [200, 201, 211, 237, 239, 250, 254]


def validate_modis_class(class_value):
    """Check if a MODIS class value is valid for analysis."""
    valid_classes = get_valid_modis_classes()
    return class_value in valid_classes


def create_modis_class_mask(class_data, invalid_classes=None):
    """Create boolean mask for invalid MODIS class values."""
    if invalid_classes is None:
        invalid_classes = get_invalid_modis_classes()
    
    return np.isin(class_data, invalid_classes)


def apply_modis_quality_mask(value_data, class_data, invalid_classes=None):
    """Apply quality mask to MODIS NDSI data, setting invalid pixels to NaN."""
    if invalid_classes is None:
        invalid_classes = get_invalid_modis_classes()
    
    invalid_mask = np.isin(class_data, invalid_classes)
    masked_data = value_data.copy()
    masked_data[invalid_mask] = np.nan
    
    return masked_data