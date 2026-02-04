"""
SnowMapPy Cloud Processing Module
==================================

Process MODIS snow cover data directly from Google Earth Engine.

This module handles the complete cloud processing pipeline:
    - Earth Engine authentication and data loading
    - Terra/Aqua fusion with quality control
    - Moving window gap-filling
    - Elevation-based snow correction

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

from .processor import (
    modis_time_series_cloud,
    process_modis_ndsi_cloud,
    process_files_array
)
from .loader import load_modis_cloud_data
from .auth import initialize_earth_engine


__all__ = [
    # Main entry points
    'process_modis_ndsi_cloud',
    'modis_time_series_cloud',
    
    # Processing
    'process_files_array',
    
    # Data loading
    'load_modis_cloud_data',
    
    # Authentication
    'initialize_earth_engine',
] 