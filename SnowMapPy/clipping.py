import os
import rasterio
from rasterio.mask import mask as rasterio_mask
import numpy as np
from .data_io import save_as_zarr
from rasterio.features import geometry_mask

# Function to check if the bounding box of the ROI overlaps with the raster
def check_overlap(src, roi):
    raster_bounds = src.bounds
    roi_bounds = roi.total_bounds
    
    overlap = (
        raster_bounds.left < roi_bounds[2] and raster_bounds.right > roi_bounds[0] and
        raster_bounds.bottom < roi_bounds[3] and raster_bounds.top > roi_bounds[1]
    )
    return overlap

# Function to clip the DEM to the region of interest (ROI)
def clip_dem_to_roi(dem_path, roi, save_dir, file_name, oparams_file=None):
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

    coords = {'y': Y[:, 0], 'x': X[0, :]}
    dims = ['y', 'x']
    name = file_name
    vname = 'DEM_BV'
    attrs = {
        'crs': crs.to_string(),
        'transform': transform.to_gdal(),
        'bounds': (bounds[0], bounds[1], bounds[2], bounds[3])
    }

    if not oparams_file:
        oparams_file = save_as_zarr(
            data=DEM_ROI,
            save_dir=save_dir,
            name=name,
            vname=vname,
            coords=coords,
            dims=dims,
            attrs=attrs,
            split_attrs=False,
            save_attrs=True
        )
    
    else:
        save_as_zarr(
            data=DEM_ROI,
            save_dir=save_dir,
            name=name,
            vname=vname,
            coords=coords,
            dims=dims,
            attrs=attrs,
            params_file=oparams_file,
            split_attrs=False,
            save_attrs=True
        )