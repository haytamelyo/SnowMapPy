"""
MODIS Data Loader
=================

Load MODIS snow cover data from Google Earth Engine.

Fetches Terra (MOD10A1) and Aqua (MYD10A1) daily snow products
for a specified region and time period.

Authors: Haytam Elyoussfi, Hatim Bechri, Mostafa Bousbaa
Version: 1.0.0
"""

import os
import sys
import warnings

# Fix PROJ database conflicts BEFORE importing any geospatial libraries
# This is critical for environments with multiple PROJ installations (e.g., PostgreSQL/PostGIS)
def _fix_proj_path():
    """Fix PROJ database path conflicts before loading geospatial libraries.
    
    The PROJ database version conflict occurs when multiple geospatial tools
    (PostgreSQL/PostGIS, rasterio, pyproj) have different PROJ versions.
    We prioritize rasterio's PROJ data since we use it for reprojection.
    """
    # First, try to find rasterio's proj_data directory (most reliable)
    try:
        # We need to find rasterio's installation path without importing it fully
        import importlib.util
        spec = importlib.util.find_spec('rasterio')
        if spec and spec.origin:
            rasterio_dir = os.path.dirname(spec.origin)
            rasterio_proj = os.path.join(rasterio_dir, 'proj_data')
            if os.path.exists(os.path.join(rasterio_proj, 'proj.db')):
                os.environ['PROJ_LIB'] = rasterio_proj
                os.environ['PROJ_DATA'] = rasterio_proj
                os.environ['GDAL_DATA'] = os.path.join(rasterio_dir, 'gdal_data')
                return
    except Exception:
        pass
    
    # Fallback: try pyproj's data directory
    try:
        import pyproj
        proj_dir = pyproj.datadir.get_data_dir()
        if proj_dir and os.path.exists(os.path.join(proj_dir, 'proj.db')):
            os.environ['PROJ_LIB'] = proj_dir
            os.environ['PROJ_DATA'] = proj_dir
    except ImportError:
        pass

_fix_proj_path()

import ee
import numpy as np
import geemap
import xarray as xr
import geopandas as gpd
from .auth import initialize_earth_engine
from ..core.console import print_info, print_success, print_error, print_warning, suppress_warnings

# Suppress warnings on module load
suppress_warnings()

# Enable automatic SHX restoration for corrupted/missing .shx files
os.environ['SHAPE_RESTORE_SHX'] = 'YES'


def _check_and_restore_shx(shapefile_path: str) -> bool:
    """
    Check if SHX file exists and is valid. Returns True if restoration was needed.
    
    The SHX file is an index file that accompanies shapefiles. If missing or corrupted,
    GDAL/Fiona can restore it when SHAPE_RESTORE_SHX='YES' is set.
    
    Parameters
    ----------
    shapefile_path : str
        Path to the .shp file.
        
    Returns
    -------
    bool
        True if SHX was missing/corrupted and restoration was triggered, False otherwise.
    """
    base_path = os.path.splitext(shapefile_path)[0]
    shx_path = base_path + '.shx'
    shp_path = base_path + '.shp'
    
    # Check if SHX file exists
    if not os.path.exists(shx_path):
        print_warning(f"SHX file missing for '{os.path.basename(shapefile_path)}'. It will be automatically restored.")
        return True
    
    # Check if SHX file is valid (basic check: should have some content)
    try:
        shx_size = os.path.getsize(shx_path)
        shp_size = os.path.getsize(shp_path)
        
        # SHX should have at least 100 bytes (header) and be proportional to SHP
        # A completely empty or tiny SHX file is likely corrupted
        if shx_size < 100:
            print_warning(f"SHX file appears corrupted for '{os.path.basename(shapefile_path)}'. It will be automatically restored.")
            return True
            
    except OSError:
        print_warning(f"Cannot verify SHX file for '{os.path.basename(shapefile_path)}'. It will be automatically restored if needed.")
        return True
    
    return False


def load_modis_cloud_data(project_name, shapefile_path, start_date, end_date, crs="EPSG:4326"):
    """
    Load MODIS NDSI data from Google Earth Engine for specified region and dates.
    
    Fetches Terra (MOD10A1) and Aqua (MYD10A1) daily snow products,
    along with SRTM DEM data for the specified study area.
    
    Parameters
    ----------
    project_name : str
        Google Earth Engine project name for authentication.
    shapefile_path : str
        Path to shapefile defining the region of interest.
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
    crs : str, optional
        Target coordinate reference system (default: 'EPSG:4326').
        Reprojection is handled on the GEE server before data transfer.
        
    Returns
    -------
    tuple
        (terra_value, aqua_value, terra_class, aqua_class, dem, roi_gdf)
        Clipped datasets (Dask-backed for lazy loading) and the region of interest GeoDataFrame.
    """
    import gc
    import dask.array as da
    from ..core.utils import calculate_optimal_chunks, validate_modis_date_range, check_aqua_availability
    
    # MEMORY OPTIMIZATION: Load directly in target CRS from GEE
    # GEE handles reprojection on the server side - no local memory needed!
    target_crs = crs
    
    # For geographic CRS, use degrees; for projected CRS, use meters
    is_geographic = target_crs == "EPSG:4326"
    
    if not initialize_earth_engine(project_name):
        raise RuntimeError("Failed to initialize Earth Engine")
    
    # Validate and adjust date range for MODIS availability
    try:
        start_date, end_date, dates_adjusted = validate_modis_date_range(
            start_date, end_date, project_name=project_name, verbose=False
        )
    except ValueError as e:
        print_error(f"Date validation error: {e}")
        raise
    
    # Check for SHX file issues before loading
    _check_and_restore_shx(shapefile_path)
    
    # Load shapefile
    roi_original = gpd.read_file(shapefile_path)
    
    # Reproject shapefile to target CRS for GEE clipping
    if roi_original.crs != target_crs:
        roi_for_ee = roi_original.to_crs(target_crs)
    else:
        roi_for_ee = roi_original.copy()
    
    # Also keep EPSG:4326 version for EE geometry conversion (required by geemap)
    roi_wgs84 = roi_original.to_crs("EPSG:4326") if roi_original.crs != "EPSG:4326" else roi_original.copy()
    
    # Convert GeoDataFrame to Earth Engine geometry (must be in EPSG:4326 for geometry)
    try:
        roi = geemap.gdf_to_ee(roi_wgs84)
    except Exception as e:
        raise RuntimeError(
            f"Failed to convert shapefile to Earth Engine geometry. "
            f"Please check if the shapefile '{shapefile_path}' is valid. "
            f"Error: {str(e)}"
        )
    
    # Prepare MODIS collections
    print_info("Preparing MODIS Terra and Aqua collections")
    terra = (ee.ImageCollection('MODIS/061/MOD10A1')
             .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
             .filterDate(start_date, end_date))
    
    # Check if Aqua data is available for this date range
    aqua_info = check_aqua_availability(start_date, end_date)
    aqua_available = aqua_info['aqua_available']
    
    if not aqua_available:
        print_warning(aqua_info['reason'])
        print_info("  → Processing will continue with Terra data only")
        aqua = None
    else:
        # Use Aqua date range (may be adjusted if start_date < Aqua launch)
        aqua_start = aqua_info['aqua_start_date']
        aqua_end = aqua_info['aqua_end_date']
        if aqua_info['reason']:
            print_info(aqua_info['reason'])
        aqua = (ee.ImageCollection('MODIS/061/MYD10A1')
                .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
                .filterDate(aqua_start, aqua_end))
    
    srtm = ee.Image("USGS/SRTMGL1_003")
    
    # Get scale based on MODIS native resolution (~500m)
    # For projected CRS: use meters; for geographic: use degrees
    if is_geographic:
        scale = terra.first().projection().nominalScale().getInfo()
        scale_value = scale * 0.00001  # Convert to degrees
    else:
        # For projected CRS (e.g., UTM), use MODIS native scale in meters (~500m)
        scale_value = 500  # meters
    
    geometry = roi.geometry()
    
    # Load data from GEE server
    print_info("Loading Terra data from Earth Engine...")
    ds_terra = xr.open_dataset(terra, engine='ee', crs=target_crs, scale=scale_value, geometry=geometry)
    
    # Load Aqua data only if available for this date range
    if aqua_available:
        print_info("Loading Aqua data from Earth Engine...")
        ds_aqua = xr.open_dataset(aqua, engine='ee', crs=target_crs, scale=scale_value, geometry=geometry)
    else:
        ds_aqua = None
    
    print_info("Loading DEM data from Earth Engine...")
    ds_dem = xr.open_dataset(ee.ImageCollection(srtm), engine='ee', crs=target_crs, scale=scale_value, geometry=geometry)
    
    # Garbage collection after loading
    gc.collect()
    
    # Split value and class data
    ds_terra_value = ds_terra[['NDSI_Snow_Cover']]
    ds_terra_class = ds_terra[['NDSI_Snow_Cover_Class']]
    
    if ds_aqua is not None:
        ds_aqua_value = ds_aqua[['NDSI_Snow_Cover']]
        ds_aqua_class = ds_aqua[['NDSI_Snow_Cover_Class']]
        # Free original Aqua dataset
        del ds_aqua
    else:
        ds_aqua_value = None
        ds_aqua_class = None
    
    # Free original Terra dataset
    del ds_terra
    gc.collect()
    
    # Detect spatial dimension names from loaded data
    sample_dims = list(ds_terra_value.dims)
    if 'x' in sample_dims and 'y' in sample_dims:
        x_dim, y_dim = 'x', 'y'
    elif 'lon' in sample_dims and 'lat' in sample_dims:
        x_dim, y_dim = 'lon', 'lat'
    else:
        # Fallback: try to find spatial dims
        x_dim = [d for d in sample_dims if d in ['x', 'lon', 'X', 'longitude']][0] if any(d in sample_dims for d in ['x', 'lon', 'X', 'longitude']) else sample_dims[-1]
        y_dim = [d for d in sample_dims if d in ['y', 'lat', 'Y', 'latitude']][0] if any(d in sample_dims for d in ['y', 'lat', 'Y', 'latitude']) else sample_dims[-2]
    
    # Rename dimensions to standardized 'lon' and 'lat' for consistency across the pipeline
    def standardize_dims(ds):
        """Rename x/y to lon/lat for consistency."""
        rename_dict = {}
        if 'x' in ds.dims and 'x' != 'lon':
            rename_dict['x'] = 'lon'
        if 'X' in ds.dims and 'X' != 'lon':
            rename_dict['X'] = 'lon'
        if 'y' in ds.dims and 'y' != 'lat':
            rename_dict['y'] = 'lat'
        if 'Y' in ds.dims and 'Y' != 'lat':
            rename_dict['Y'] = 'lat'
        if rename_dict:
            ds = ds.rename(rename_dict)
        return ds
    
    ds_terra_value = standardize_dims(ds_terra_value)
    ds_terra_class = standardize_dims(ds_terra_class)
    if ds_aqua_value is not None:
        ds_aqua_value = standardize_dims(ds_aqua_value)
        ds_aqua_class = standardize_dims(ds_aqua_class)
    ds_dem = standardize_dims(ds_dem)
    
    # Set spatial dimensions and CRS (data is already in target_crs from GEE)
    ds_terra_value = ds_terra_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_terra_value = ds_terra_value.rio.write_crs(target_crs)
    ds_terra_class = ds_terra_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_terra_class = ds_terra_class.rio.write_crs(target_crs)
    if ds_aqua_value is not None:
        ds_aqua_value = ds_aqua_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
        ds_aqua_value = ds_aqua_value.rio.write_crs(target_crs)
        ds_aqua_class = ds_aqua_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
        ds_aqua_class = ds_aqua_class.rio.write_crs(target_crs)
    ds_dem = ds_dem.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_dem = ds_dem.rio.write_crs(target_crs)
    
    # Clip datasets to study area
    roi_geo = [roi_for_ee.geometry.values[0].__geo_interface__]
    
    ds_terra_value_clipped = ds_terra_value.rio.clip(roi_geo, target_crs, drop=False)
    ds_terra_class_clipped = ds_terra_class.rio.clip(roi_geo, target_crs, drop=False)
    if ds_aqua_value is not None:
        ds_aqua_value_clipped = ds_aqua_value.rio.clip(roi_geo, target_crs, drop=False)
        ds_aqua_class_clipped = ds_aqua_class.rio.clip(roi_geo, target_crs, drop=False)
    else:
        ds_aqua_value_clipped = None
        ds_aqua_class_clipped = None
    ds_dem_clipped = ds_dem.rio.clip(roi_geo, target_crs, drop=False)
    
    # Free unclipped datasets
    del ds_terra_value, ds_terra_class, ds_dem
    if ds_aqua_value is not None:
        del ds_aqua_value, ds_aqua_class
    gc.collect()
    
    # Apply Dask lazy loading with optimal chunking
    sample_shape = ds_terra_value_clipped['NDSI_Snow_Cover'].shape
    
    # Calculate optimal chunks based on data dimensions
    if len(sample_shape) == 3:
        optimal_chunks = calculate_optimal_chunks(sample_shape, dtype=np.float32)
        chunk_dict = {'lat': optimal_chunks[0], 'lon': optimal_chunks[1], 'time': optimal_chunks[2]}
    else:
        optimal_chunks = calculate_optimal_chunks(sample_shape, dtype=np.float32)
        chunk_dict = {dim: optimal_chunks[i] for i, dim in enumerate(ds_terra_value_clipped.dims)}
    
    # Apply chunking to all datasets - this makes them Dask-backed and lazy
    ds_terra_value_clipped = ds_terra_value_clipped.chunk(chunk_dict)
    ds_terra_class_clipped = ds_terra_class_clipped.chunk(chunk_dict)
    if ds_aqua_value_clipped is not None:
        ds_aqua_value_clipped = ds_aqua_value_clipped.chunk(chunk_dict)
        ds_aqua_class_clipped = ds_aqua_class_clipped.chunk(chunk_dict)
    
    # DEM may have a singleton time dimension - squeeze it out
    if 'time' in ds_dem_clipped.dims:
        ds_dem_clipped = ds_dem_clipped.isel(time=0, drop=True)
    
    # DEM has no time dimension - chunk only spatial dims
    dem_dims = [d for d in ds_dem_clipped.dims if d in ('lat', 'lon')]
    dem_chunks = {d: chunk_dict.get(d, -1) for d in dem_dims}
    ds_dem_clipped = ds_dem_clipped.chunk(dem_chunks)
    
    # Sort latitude in descending order (north at top)
    ds_terra_value_clipped = ds_terra_value_clipped.sortby('lat', ascending=False)
    ds_terra_class_clipped = ds_terra_class_clipped.sortby('lat', ascending=False)
    if ds_aqua_value_clipped is not None:
        ds_aqua_value_clipped = ds_aqua_value_clipped.sortby('lat', ascending=False)
        ds_aqua_class_clipped = ds_aqua_class_clipped.sortby('lat', ascending=False)
    ds_dem_clipped = ds_dem_clipped.sortby('lat', ascending=False)
    
    roi_checker = roi_for_ee
    
    print_info("Clipping data to study area...")
    print_success("Data loaded successfully")
    
    return (
        ds_terra_value_clipped,
        ds_aqua_value_clipped, 
        ds_terra_class_clipped,
        ds_aqua_class_clipped,
        ds_dem_clipped,
        roi_checker
    )