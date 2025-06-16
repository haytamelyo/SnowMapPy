import os
import rasterio
import datetime
import numpy as np
from tqdm import tqdm
from rasterio.features import geometry_mask
from .clipping import clip_dem_to_roi, check_overlap
from rasterio.mask import mask as rasterio_mask
from .data_io import save_as_zarr, load_shapefile
from .reprojection import reproject_shp, handle_reprojection


# Main function to process directories and reproject data
def prepare_modis(data_dir, save_dir, dem_path, shp_path, oparams_file=None, priority='MODIS', save_name='MODIS', save_dem=True, dem_name='DEM'):
    
    roi = load_shapefile(shp_path)
    
    os.chdir(data_dir)
    D = os.listdir(data_dir)

    modis_save_dir = os.path.join(save_dir, save_name)
    if not os.path.exists(modis_save_dir):
        os.makedirs(modis_save_dir)

    if save_dem:
        dem_save_dir = os.path.join(save_dir, 'DEM')
        if not os.path.exists(dem_save_dir):
            os.makedirs(dem_save_dir)

    for k in tqdm(range(len(D)), desc="Processing directories"):
        currD = os.path.join(data_dir, D[k])
        flist = os.listdir(currD)
        
        os.chdir(currD)
        
        scfile = [f for f in flist if 'Snow_Cover' in f and f.endswith('.tif')]
        
        if not scfile:
            tqdm.write('No Snow Cover data found.')
            continue
        
        fname = scfile[0]
        DateSve = datetime.datetime.strptime(fname[9:16], '%Y%j').strftime('%Y-%m-%d')

        img_path = os.path.join(currD, scfile[0])

        if priority == 'MODIS' and k == 0:
            dem_file = dem_path.split('\\')[-1]
            if save_dem:
                reprojected_dem = os.path.join(dem_save_dir, f"reprojected_{dem_file}")
            elif not save_dem:
                dem_dir = dem_path.rsplit('\\', 1)[0]
                reprojected_dem = os.path.join(dem_dir, f"reprojected_{dem_file}")
            handle_reprojection(img_path, dem_path, reprojected_dem, priority=priority)
            dem_path = reprojected_dem

        elif priority == 'DEM':
            reprojected_image = os.path.join(save_dir, f"reprojected_{scfile[0]}")
            handle_reprojection(img_path, dem_path, reprojected_image, priority=priority)
            img_path = reprojected_image

        with rasterio.open(img_path) as src:
            if k == 0:
                reprojected_roi = reproject_shp(roi, src.crs)

            if not check_overlap(src, reprojected_roi):
                tqdm.write(f"ROI does not overlap with raster in directory {currD}. Skipping...")
                continue

            try:
                SCA_crs = src.crs
                SCA, out_transf = rasterio_mask(src, [reprojected_roi.geometry.iloc[0]], crop=True, all_touched=True, pad=True)
                SCA = SCA[0]

            except ValueError as e:
                tqdm.write(f"Masking failed in directory {currD}: {e}")
                continue
        
        if k == 0:
            ROI_mask = geometry_mask(reprojected_roi.geometry, transform=out_transf, invert=True, out_shape=SCA.shape)
            ROI_mask = np.where(ROI_mask == 0, np.nan, 1)
        
        if SCA.shape != ROI_mask.shape:
            raise ValueError(f"Shapes do not match: SCA shape {SCA.shape}, ROI_mask shape {ROI_mask.shape}")

        SCA_ROI = SCA * ROI_mask
        
        transform = out_transf
        
        bounds = rasterio.transform.array_bounds(SCA.shape[0], SCA.shape[1], transform)
        X, Y = np.meshgrid(np.linspace(bounds[0], bounds[2], SCA.shape[1]),
                           np.linspace(bounds[3], bounds[1], SCA.shape[0]))
        
        coords = {'y': Y[:, 0], 'x': X[0, :]}
        dims = ['y', 'x']
        vname = 'SCA'
        zarr_name = save_name + '_' + DateSve
        attrs = {
            'crs': SCA_crs.to_string(),
            'transform': transform.to_gdal(),
            'bounds': (bounds[0], bounds[1], bounds[2], bounds[3])
        }

        if k == 0 and oparams_file == None:
            oparams_file = save_as_zarr(
                data=SCA_ROI,
                save_dir=modis_save_dir,
                name=zarr_name,
                vname=vname,
                coords=coords,
                dims=dims,
                attrs=attrs,
                split_attrs=True,
                save_attrs=True
            )
        
        elif k == 0 and oparams_file != None:
            oparams_file = save_as_zarr(
                data=SCA_ROI,
                save_dir=modis_save_dir,
                name=zarr_name,
                vname=vname,
                coords=coords,
                dims=dims,
                attrs=attrs,
                params_file=oparams_file,
                split_attrs=True,
                save_attrs=True
            )

        else:
            save_as_zarr(
                data=SCA_ROI,
                save_dir=modis_save_dir,
                name=zarr_name,
                vname=vname,
                dims=dims,
                params_file=oparams_file,
                split_attrs=False,
                save_attrs=False
            )
        
        if save_dem and k == 0:
            clip_dem_to_roi(dem_path, reprojected_roi, dem_save_dir, dem_name, oparams_file)
