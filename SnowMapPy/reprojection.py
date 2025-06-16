import rasterio
from rasterio.warp import reproject, Resampling

# Function to reproject a raster
def reproject_raster(src_path, dst_path, src_transform, src_crs, dst_transform, dst_crs, shape, method=Resampling.nearest):
    with rasterio.open(src_path) as src:
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': dst_transform,
            'width': shape[1],
            'height': shape[0]
        })
        
        with rasterio.open(dst_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src_transform or src.transform,
                    src_crs=src.crs if not src_crs else src_crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=method
                )


# Function to reproject a GeoDataFrame (ROI) to match raster CRS
def reproject_shp(roi, target_crs):
    return roi.to_crs(target_crs)


# Function to process data and reproject based on the priority (MODIS or DEM)
def handle_reprojection(modis_path, dem_path, output_path, priority='MODIS'):
    if priority == 'MODIS':
        with rasterio.open(modis_path) as modis_src:
            modis_transform = modis_src.transform
            modis_shape = modis_src.shape
            modis_crs = modis_src.crs

        reproject_raster(dem_path, output_path, src_transform=None, 
                         src_crs=None, dst_transform=modis_transform,
                         dst_crs=modis_crs, shape=modis_shape)

    else:
        with rasterio.open(dem_path) as dem_src:
            dem_transform = dem_src.transform
            dem_shape = dem_src.shape
            dem_crs = dem_src.crs

        reproject_raster(modis_path, output_path, src_transform=None, 
                         src_crs=None, dst_transform=dem_transform,
                         dst_crs=dem_crs, shape=dem_shape)
