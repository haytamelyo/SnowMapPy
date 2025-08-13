import os
import rasterio
import xarray as xr
from rasterio.mask import mask as rasterio_mask
import numpy as np
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling
from .data_io import save_as_zarr


def check_overlap(src, roi):
    """
    Check if the bounding box of the ROI overlaps with the raster.
    """
    raster_bounds = src.bounds
    roi_bounds = roi.total_bounds
    
    overlap = (
        raster_bounds.left < roi_bounds[2] and raster_bounds.right > roi_bounds[0] and
        raster_bounds.bottom < roi_bounds[3] and raster_bounds.top > roi_bounds[1]
    )
    return overlap


def clip_dem_to_roi(dem_path, roi, save_dir, file_name, oparams_file=None):
    """
    Clip the DEM to the region of interest (ROI).
    """
    os.environ['SHAPE_RESTORE_SHX'] = 'YES'

    with rasterio.open(dem_path) as src:
        DEM = src.read(1).astype(np.float64)
        transform = src.transform
        crs = src.crs

    DEM[DEM == 65536] = np.nan

    with rasterio.open(dem_path) as src:
        DEM_clipped, out_transform = rasterio_mask(src, [roi.geometry.iloc[0]], crop=True, all_touched=True, pad=True)
        DEM_clipped = DEM_clipped[0]

    ROI_mask = geometry_mask(roi.geometry, transform=out_transform, invert=True, out_shape=DEM_clipped.shape)
    ROI_mask = np.where(ROI_mask == 0, np.nan, 1)

    if DEM_clipped.shape != ROI_mask.shape:
        raise ValueError(f"Shapes do not match: DEM_clipped shape {DEM_clipped.shape}, ROI_mask shape {ROI_mask.shape}")

    DEM_ROI = DEM_clipped * ROI_mask

    bounds = rasterio.transform.array_bounds(DEM_ROI.shape[0], DEM_ROI.shape[1], transform)
    X, Y = np.meshgrid(np.linspace(bounds[0], bounds[2], DEM_ROI.shape[1]),
                       np.linspace(bounds[3], bounds[1], DEM_ROI.shape[0]))

    lat = Y[:, 0].tolist()
    lon = X[0, :].tolist()

    ds = xr.Dataset(
        data_vars={
            'elevation': (('lat', 'lon'), DEM_ROI)
        },
        coords={
            'lat': lat,
            'lon': lon
        },
        attrs={
            'crs': crs.to_string(),
            'transform': out_transform.to_gdal(),
            'bounds': bounds
        }
    )

    save_as_zarr(ds, save_dir, file_name, oparams_file)
    return ds


def reproject_raster(src_path, dst_path, src_transform, src_crs, dst_transform, dst_crs, shape, method=Resampling.nearest):
    """
    Reproject a raster.
    """
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


def reproject_shp(roi, target_crs):
    """
    Reproject a GeoDataFrame (ROI) to match raster CRS.
    """
    return roi.to_crs(target_crs)


def handle_reprojection(modis_path, dem_path, output_path, priority='MODIS'):
    """
    Process data and reproject based on the priority (MODIS or DEM).
    """
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