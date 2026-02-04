"""
MODIS Data Loader
=================

Load MODIS snow cover data from Google Earth Engine.

Fetches Terra (MOD10A1) and Aqua (MYD10A1) daily snow products
for a specified region and time period.

Authors: Haytam Elyoussfi, Hatim Bechri, Mostafa Bousbaa
Version: 2.0.0
"""

import ee
import geemap
import xarray as xr
import geopandas as gpd
from .auth import initialize_earth_engine
from ..core.console import print_info, print_success, print_error, print_warning, suppress_warnings
import os
import warnings

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
        Coordinate reference system (default: 'EPSG:4326').
        
    Returns
    -------
    tuple
        (terra_value, aqua_value, terra_class, aqua_class, dem, roi_gdf)
        Clipped datasets and the region of interest GeoDataFrame.
    """
    
    if not initialize_earth_engine(project_name):
        raise RuntimeError("Failed to initialize Earth Engine")
    
    # Check for SHX file issues before loading
    _check_and_restore_shx(shapefile_path)
    
    # Load and reproject shapefile if needed
    roi_checker = gpd.read_file(shapefile_path)
    
    if roi_checker.crs != crs:
        print_info(f"Reprojecting shapefile to {crs}")
        roi_checker = roi_checker.to_crs(crs)
        base_dir = os.path.dirname(shapefile_path)
        reprojected_path = os.path.join(base_dir, "reprojected_shapefile.shp")
        roi_checker.to_file(reprojected_path)
        shapefile_path = reprojected_path
        _check_and_restore_shx(reprojected_path)

    # Convert GeoDataFrame to Earth Engine geometry
    try:
        roi = geemap.gdf_to_ee(roi_checker)
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
    
    # Load datasets sequentially (Earth Engine requires single-threaded access)
    print_info("Loading Terra data from Earth Engine...")
    ds_terra = xr.open_dataset(terra, engine='ee', crs=crs, scale=scale_deg, geometry=geometry)
    print_info("  ✓ Terra data loaded")
    
    print_info("Loading Aqua data from Earth Engine...")
    ds_aqua = xr.open_dataset(aqua, engine='ee', crs=crs, scale=scale_deg, geometry=geometry)
    print_info("  ✓ Aqua data loaded")
    
    print_info("Loading DEM data from Earth Engine...")
    ds_dem = xr.open_dataset(ee.ImageCollection(srtm), engine='ee', crs=crs, scale=scale_deg, geometry=geometry)
    print_info("  ✓ DEM data loaded")
    
    # Split value and class data
    ds_terra_value = ds_terra[['NDSI_Snow_Cover']]
    ds_terra_class = ds_terra[['NDSI_Snow_Cover_Class']]
    ds_aqua_value = ds_aqua[['NDSI_Snow_Cover']]
    ds_aqua_class = ds_aqua[['NDSI_Snow_Cover_Class']]
    
    # Set spatial dimensions
    ds_terra_value = ds_terra_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_terra_class = ds_terra_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_aqua_value = ds_aqua_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_aqua_class = ds_aqua_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_dem = ds_dem.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    
    # Clip datasets to study area
    print_info("Clipping data to study area...")
    ds_terra_value_clipped = ds_terra_value.rio.clip(roi_geo, crs, drop=False)
    ds_terra_class_clipped = ds_terra_class.rio.clip(roi_geo, crs, drop=False)
    ds_aqua_value_clipped = ds_aqua_value.rio.clip(roi_geo, crs, drop=False)
    ds_aqua_class_clipped = ds_aqua_class.rio.clip(roi_geo, crs, drop=False)
    ds_dem_clipped = ds_dem.rio.clip(roi_geo, crs, drop=False)
    print_info("  ✓ All data clipped to study area")
    
    print_success("All data loaded and clipped successfully")
    
    return (
        ds_terra_value_clipped,
        ds_aqua_value_clipped, 
        ds_terra_class_clipped,
        ds_aqua_class_clipped,
        ds_dem_clipped,
        roi_checker
    )