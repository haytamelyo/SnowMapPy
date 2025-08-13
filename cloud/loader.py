import ee
import geemap
import xarray as xr
import geopandas as gpd
from .auth import initialize_earth_engine
import os


def load_modis_cloud_data(project_name, shapefile_path, start_date, end_date, crs="EPSG:4326"):
    """
    Load MODIS data from Google Earth Engine.
    
    Args:
        project_name: Google Cloud project name
        shapefile_path: Path to ROI shapefile
        start_date: Start date for data collection
        end_date: End date for data collection
        crs: Coordinate reference system
        
    Returns:
        tuple: (terra_value, aqua_value, terra_class, aqua_class, dem, roi)
    """
    # Initialize Earth Engine
    if not initialize_earth_engine(project_name):
        raise RuntimeError("Failed to initialize Earth Engine")
    
    # Load the shapefile using geopandas
    roi_checker = gpd.read_file(shapefile_path)
    
    # If the shapefile's CRS doesn't match the desired CRS, reproject it
    if roi_checker.crs != crs:
        print(f"Reprojecting the shapefile to {crs}")
        roi_checker = roi_checker.to_crs(crs)
        base_dir = os.path.dirname(shapefile_path)
        reprojected_path = os.path.join(base_dir, "reprojected_shapefile.shp")
        roi_checker.to_file(reprojected_path)
        shapefile_path = reprojected_path

    # Convert the shapefile to an Earth Engine object
    roi = geemap.shp_to_ee(shapefile_path)
    
    # Load MODIS Terra and Aqua NDSI data using the specified dates
    print("Loading MODIS Terra and Aqua NDSI data")
    terra = (ee.ImageCollection('MODIS/061/MOD10A1')
             .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
             .filterDate(start_date, end_date))
    aqua = (ee.ImageCollection('MODIS/061/MYD10A1')
            .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
            .filterDate(start_date, end_date))
    
    # Extract the scale (resolution) from the MODIS data and convert it to degrees
    scale = terra.first().projection().nominalScale().getInfo()
    scale_deg = scale * 0.00001
    
    # Load the Earth Engine collections into xarray datasets
    print("Loading the MODIS data in xarray")
    ds_terra = xr.open_dataset(terra, engine='ee', crs=crs, scale=scale_deg, geometry=roi.geometry())
    ds_aqua = xr.open_dataset(aqua, engine='ee', crs=crs, scale=scale_deg, geometry=roi.geometry())
    
    # Split into value and class datasets
    ds_terra_value = ds_terra[['NDSI_Snow_Cover']]
    ds_terra_class = ds_terra[['NDSI_Snow_Cover_Class']]
    ds_aqua_value = ds_aqua[['NDSI_Snow_Cover']]
    ds_aqua_class = ds_aqua[['NDSI_Snow_Cover_Class']]
    
    # Set spatial dimensions
    ds_terra_value = ds_terra_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_terra_class = ds_terra_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_aqua_value = ds_aqua_value.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    ds_aqua_class = ds_aqua_class.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
    
    # Convert Earth Engine geometry to a dictionary and wrap it in a list
    roi_geo = [roi.geometry().getInfo()]
    print("Clipping the MODIS data to the study area")
    ds_terra_value_clipped = ds_terra_value.rio.clip(roi_geo, crs, drop=False)
    ds_terra_class_clipped = ds_terra_class.rio.clip(roi_geo, crs, drop=False)
    ds_aqua_value_clipped = ds_aqua_value.rio.clip(roi_geo, crs, drop=False)
    ds_aqua_class_clipped = ds_aqua_class.rio.clip(roi_geo, crs, drop=False)
    
    # Load SRTM DEM data
    print("Loading SRTM DEM data")
    srtm = ee.Image("USGS/SRTMGL1_003")
    ds_dem = xr.open_dataset(srtm, engine='ee', crs=crs, scale=scale_deg, geometry=roi.geometry())
    ds_dem = ds_dem.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)

    print("Clipping the DEM data to the study area")
    ds_dem_clipped = ds_dem.rio.clip(roi_geo, crs, drop=False)
    
    return (ds_terra_value_clipped, ds_aqua_value_clipped, 
            ds_terra_class_clipped, ds_aqua_class_clipped, 
            ds_dem_clipped, roi_checker) 