"""
MODIS Data Loader
=================

Load MODIS snow cover data from Google Earth Engine.

Fetches Terra (MOD10A1) and Aqua (MYD10A1) daily snow products
for a specified region and time period.

Authors: Haytam Elyoussfi, Hatim Bechri, Mostafa Bousbaa
Version: 2.0.0
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
    
    Note: Data is always loaded from Earth Engine in EPSG:4326 (geographic coordinates)
    and then reprojected to the target CRS. This is because the xee library has issues
    with projected CRS (like UTM) during data loading.
    
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
        Data will be reprojected to this CRS after loading.
        
    Returns
    -------
    tuple
        (terra_value, aqua_value, terra_class, aqua_class, dem, roi_gdf)
        Clipped datasets and the region of interest GeoDataFrame.
    """
    # Always load from Earth Engine in geographic coordinates
    # Then reproject to target CRS - xee has issues with projected CRS
    load_crs = "EPSG:4326"
    target_crs = crs
    needs_reprojection = (target_crs != load_crs)
    
    if not initialize_earth_engine(project_name):
        raise RuntimeError("Failed to initialize Earth Engine")
    
    # Check for SHX file issues before loading
    _check_and_restore_shx(shapefile_path)
    
    # Load shapefile and reproject to EPSG:4326 for Earth Engine loading
    roi_original = gpd.read_file(shapefile_path)
    
    # Keep original for final output, create EPSG:4326 version for EE loading
    if roi_original.crs != load_crs:
        roi_for_ee = roi_original.to_crs(load_crs)
    else:
        roi_for_ee = roi_original.copy()
    
    # Convert GeoDataFrame to Earth Engine geometry (must be in EPSG:4326)
    try:
        roi = geemap.gdf_to_ee(roi_for_ee)
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
    aqua = (ee.ImageCollection('MODIS/061/MYD10A1')
            .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
            .filterDate(start_date, end_date))
    srtm = ee.Image("USGS/SRTMGL1_003")
    
    # Get scale and convert to degrees
    scale = terra.first().projection().nominalScale().getInfo()
    scale_deg = scale * 0.00001
    
    geometry = roi.geometry()
    roi_geo = [geometry.getInfo()]
    
    # Load datasets sequentially in EPSG:4326 (Earth Engine native CRS)
    # This avoids hanging issues with projected CRS in xee
    print_info("Loading Terra data from Earth Engine...")
    ds_terra = xr.open_dataset(terra, engine='ee', crs=load_crs, scale=scale_deg, geometry=geometry)
    print_info("  ✓ Terra data loaded")
    
    print_info("Loading Aqua data from Earth Engine...")
    ds_aqua = xr.open_dataset(aqua, engine='ee', crs=load_crs, scale=scale_deg, geometry=geometry)
    print_info("  ✓ Aqua data loaded")
    
    print_info("Loading DEM data from Earth Engine...")
    ds_dem = xr.open_dataset(ee.ImageCollection(srtm), engine='ee', crs=load_crs, scale=scale_deg, geometry=geometry)
    print_info("  ✓ DEM data loaded")
    
    # Split value and class data
    ds_terra_value = ds_terra[['NDSI_Snow_Cover']]
    ds_terra_class = ds_terra[['NDSI_Snow_Cover_Class']]
    ds_aqua_value = ds_aqua[['NDSI_Snow_Cover']]
    ds_aqua_class = ds_aqua[['NDSI_Snow_Cover_Class']]
    
    # Set spatial dimensions and CRS for clipping
    ds_terra_value = ds_terra_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_terra_value = ds_terra_value.rio.write_crs(load_crs)
    ds_terra_class = ds_terra_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_terra_class = ds_terra_class.rio.write_crs(load_crs)
    ds_aqua_value = ds_aqua_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_aqua_value = ds_aqua_value.rio.write_crs(load_crs)
    ds_aqua_class = ds_aqua_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_aqua_class = ds_aqua_class.rio.write_crs(load_crs)
    ds_dem = ds_dem.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_dem = ds_dem.rio.write_crs(load_crs)
    
    # Clip datasets to study area (in EPSG:4326)
    print_info("Clipping data to study area...")
    ds_terra_value_clipped = ds_terra_value.rio.clip(roi_geo, load_crs, drop=False)
    ds_terra_class_clipped = ds_terra_class.rio.clip(roi_geo, load_crs, drop=False)
    ds_aqua_value_clipped = ds_aqua_value.rio.clip(roi_geo, load_crs, drop=False)
    ds_aqua_class_clipped = ds_aqua_class.rio.clip(roi_geo, load_crs, drop=False)
    ds_dem_clipped = ds_dem.rio.clip(roi_geo, load_crs, drop=False)
    print_info("  ✓ All data clipped to study area")
    
    # Reproject to target CRS if needed
    if needs_reprojection:
        print_info(f"Reprojecting data to {target_crs}...")
        
        def reproject_dataset(ds, crs, resampling=None):
            """Reproject dataset handling dimension order and renaming coords."""
            result_vars = {}
            
            for var in ds.data_vars:
                arr = ds[var]
                dims = arr.dims
                
                # Find spatial dimensions
                spatial_dims = [d for d in dims if d in ['lat', 'lon', 'y', 'x']]
                other_dims = [d for d in dims if d not in spatial_dims]
                
                # Reorder to (other..., y, x) for reprojection
                if spatial_dims:
                    y_dim = 'lat' if 'lat' in spatial_dims else 'y'
                    x_dim = 'lon' if 'lon' in spatial_dims else 'x'
                    new_order = other_dims + [y_dim, x_dim]
                    arr = arr.transpose(*new_order)
                else:
                    y_dim = 'lat'
                    x_dim = 'lon'
                
                # Set spatial dims and CRS
                arr = arr.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim, inplace=False)
                arr = arr.rio.write_crs(ds.rio.crs, inplace=False)
                
                # Reproject
                if resampling is not None:
                    arr = arr.rio.reproject(crs, resampling=resampling)
                else:
                    arr = arr.rio.reproject(crs)
                
                # Rename x/y back to lon/lat for consistency
                if 'x' in arr.dims and 'y' in arr.dims:
                    arr = arr.rename({'x': 'lon', 'y': 'lat'})
                
                result_vars[var] = arr
            
            # Create new dataset from reprojected arrays
            result = xr.Dataset(result_vars)
            result = result.rio.write_crs(crs)
            
            return result
        
        ds_terra_value_clipped = reproject_dataset(ds_terra_value_clipped, target_crs)
        ds_terra_class_clipped = reproject_dataset(ds_terra_class_clipped, target_crs, resampling=0)  # Nearest for classes
        ds_aqua_value_clipped = reproject_dataset(ds_aqua_value_clipped, target_crs)
        ds_aqua_class_clipped = reproject_dataset(ds_aqua_class_clipped, target_crs, resampling=0)  # Nearest for classes
        ds_dem_clipped = reproject_dataset(ds_dem_clipped, target_crs)
        # Also reproject the ROI GeoDataFrame
        roi_checker = roi_original.to_crs(target_crs) if roi_original.crs != target_crs else roi_original
        print_info(f"  ✓ All data reprojected to {target_crs}")
    else:
        roi_checker = roi_for_ee
    
    
    print_success("All data loaded and clipped successfully")
    
    return (
        ds_terra_value_clipped,
        ds_aqua_value_clipped, 
        ds_terra_class_clipped,
        ds_aqua_class_clipped,
        ds_dem_clipped,
        roi_checker
    )