import ee
import geemap
import xarray as xr
import geopandas as gpd
from .auth import initialize_earth_engine
import os


def load_modis_cloud_data(project_name, shapefile_path, start_date, end_date, crs="EPSG:4326"):
    """Load MODIS NDSI data from Google Earth Engine for specified region and dates."""
    
    if not initialize_earth_engine(project_name):
        raise RuntimeError("Failed to initialize Earth Engine")
    
    # Load and reproject shapefile if needed
    roi_checker = gpd.read_file(shapefile_path)
    
    if roi_checker.crs != crs:
        print(f"Reprojecting the shapefile to {crs}")
        roi_checker = roi_checker.to_crs(crs)
        base_dir = os.path.dirname(shapefile_path)
        reprojected_path = os.path.join(base_dir, "reprojected_shapefile.shp")
        roi_checker.to_file(reprojected_path)
        shapefile_path = reprojected_path

    # Convert shapefile to Earth Engine geometry
    roi = geemap.shp_to_ee(shapefile_path)
    
    # Load MODIS collections
    print("Loading MODIS Terra and Aqua NDSI data")
    terra = (ee.ImageCollection('MODIS/061/MOD10A1')
             .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
             .filterDate(start_date, end_date))
    aqua = (ee.ImageCollection('MODIS/061/MYD10A1')
            .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class'])
            .filterDate(start_date, end_date))
    
    # Get scale and convert to degrees
    scale = terra.first().projection().nominalScale().getInfo()
    scale_deg = scale * 0.00001
    
    # Load into xarray datasets
    print("Loading the MODIS data in xarray")
    ds_terra = xr.open_dataset(terra, engine='ee', crs=crs, scale=scale_deg, geometry=roi.geometry())
    ds_aqua = xr.open_dataset(aqua, engine='ee', crs=crs, scale=scale_deg, geometry=roi.geometry())
    
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
    
    # Clip to study area
    roi_geo = [roi.geometry().getInfo()]
    print("Clipping the MODIS data to the study area")
    ds_terra_value_clipped = ds_terra_value.rio.clip(roi_geo, crs, drop=False)
    ds_terra_class_clipped = ds_terra_class.rio.clip(roi_geo, crs, drop=False)
    ds_aqua_value_clipped = ds_aqua_value.rio.clip(roi_geo, crs, drop=False)
    ds_aqua_class_clipped = ds_aqua_class.rio.clip(roi_geo, crs, drop=False)
    
    # Load and clip DEM data
    print("Loading SRTM DEM data")
    srtm = ee.Image("USGS/SRTMGL1_003")
    ds_dem = xr.open_dataset(srtm, engine='ee', crs=crs, scale=scale_deg, geometry=roi.geometry())
    ds_dem = ds_dem.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)

    print("Clipping the DEM data to the study area")
    ds_dem_clipped = ds_dem.rio.clip(roi_geo, crs, drop=False)
    
    return (ds_terra_value_clipped, ds_aqua_value_clipped, 
            ds_terra_class_clipped, ds_aqua_class_clipped, 
            ds_dem_clipped, roi_checker)