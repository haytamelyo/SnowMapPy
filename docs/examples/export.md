# Export Workflows

Export SnowMapPy results to various formats for use in GIS software and other applications.

---

## Overview

SnowMapPy outputs data in Zarr format by default. This guide shows how to export to other common formats.

---

## Export to GeoTIFF

### Single Time Step

Export one day as a GeoTIFF:

```python
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
import numpy as np

# Load data
ds = xr.open_zarr('./output/snow_cover.zarr')

# Select a specific date
date = '2020-02-15'
data = ds['NDSI'].sel(time=date, method='nearest').values

# Handle NaN values
data = np.nan_to_num(data, nan=-9999)

# Create geotransform
transform = from_bounds(
    float(ds.x.min()), float(ds.y.min()),
    float(ds.x.max()), float(ds.y.max()),
    data.shape[1], data.shape[0]
)

# Write GeoTIFF
with rasterio.open(
    f'snow_cover_{date}.tif',
    'w',
    driver='GTiff',
    height=data.shape[0],
    width=data.shape[1],
    count=1,
    dtype='float32',
    crs='EPSG:4326',
    transform=transform,
    nodata=-9999,
    compress='lzw'
) as dst:
    dst.write(data.astype('float32'), 1)
    dst.update_tags(date=date, source='SnowMapPy')

print(f"Saved: snow_cover_{date}.tif")
```

### Multi-Band Stack

Export all time steps as a multi-band GeoTIFF:

```python
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
import numpy as np

ds = xr.open_zarr('./output/snow_cover.zarr')
data = ds['NDSI'].values  # (time, y, x)
data = np.nan_to_num(data, nan=-9999)

transform = from_bounds(
    float(ds.x.min()), float(ds.y.min()),
    float(ds.x.max()), float(ds.y.max()),
    data.shape[2], data.shape[1]
)

with rasterio.open(
    'snow_cover_stack.tif',
    'w',
    driver='GTiff',
    height=data.shape[1],
    width=data.shape[2],
    count=data.shape[0],
    dtype='float32',
    crs='EPSG:4326',
    transform=transform,
    nodata=-9999,
    compress='lzw'
) as dst:
    for i in range(data.shape[0]):
        dst.write(data[i].astype('float32'), i + 1)
        # Add date as band description
        dst.set_band_description(i + 1, str(ds.time.values[i])[:10])

print(f"Saved: snow_cover_stack.tif ({data.shape[0]} bands)")
```

### Batch Export

Export each day as a separate GeoTIFF:

```python
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
import numpy as np
from tqdm import tqdm

ds = xr.open_zarr('./output/snow_cover.zarr')
output_dir = Path('./geotiffs')
output_dir.mkdir(exist_ok=True)

transform = from_bounds(
    float(ds.x.min()), float(ds.y.min()),
    float(ds.x.max()), float(ds.y.max()),
    ds.dims['x'], ds.dims['y']
)

for i, time in enumerate(tqdm(ds.time.values, desc="Exporting")):
    date_str = str(time)[:10]
    data = ds['NDSI'].isel(time=i).values
    data = np.nan_to_num(data, nan=-9999)
    
    output_path = output_dir / f'snow_{date_str}.tif'
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype='float32',
        crs='EPSG:4326',
        transform=transform,
        nodata=-9999,
        compress='lzw'
    ) as dst:
        dst.write(data.astype('float32'), 1)

print(f"Exported {len(ds.time)} GeoTIFFs to {output_dir}/")
```

---

## Export to NetCDF

### Full Dataset

```python
import xarray as xr

ds = xr.open_zarr('./output/snow_cover.zarr')

# Add attributes
ds.attrs['title'] = 'MODIS NDSI Snow Cover'
ds.attrs['source'] = 'SnowMapPy'
ds.attrs['Conventions'] = 'CF-1.8'

# Save as NetCDF4
ds.to_netcdf(
    'snow_cover.nc',
    engine='netcdf4',
    encoding={
        'NDSI': {
            'dtype': 'float32',
            'zlib': True,
            'complevel': 4
        }
    }
)
```

### Subset Before Export

```python
import xarray as xr

ds = xr.open_zarr('./output/snow_cover.zarr')

# Temporal subset
winter = ds.sel(time=slice('2020-12-01', '2021-02-28'))
winter.to_netcdf('winter_2020_2021.nc')

# Spatial subset
subset = ds.sel(x=slice(-8.0, -6.0), y=slice(34.0, 32.0))
subset.to_netcdf('subset_region.nc')

# Monthly mean
monthly = ds.resample(time='1M').mean()
monthly.to_netcdf('monthly_mean.nc')
```

---

## Export to CSV

### Point Time Series

```python
import xarray as xr
import pandas as pd

ds = xr.open_zarr('./output/snow_cover.zarr')

# Define analysis points
points = {
    'station_A': (33.5, -7.2),
    'station_B': (32.8, -6.5),
    'station_C': (34.1, -7.8)
}

# Extract time series
records = []
for name, (lat, lon) in points.items():
    ts = ds['NDSI'].sel(y=lat, x=lon, method='nearest')
    for i, time in enumerate(ds.time.values):
        records.append({
            'station': name,
            'date': str(time)[:10],
            'latitude': lat,
            'longitude': lon,
            'ndsi': float(ts.isel(time=i).values)
        })

df = pd.DataFrame(records)
df.to_csv('point_timeseries.csv', index=False)
print(f"Saved: point_timeseries.csv ({len(df)} records)")
```

### Regional Statistics

```python
import xarray as xr
import pandas as pd
import numpy as np

ds = xr.open_zarr('./output/snow_cover.zarr')

# Calculate daily regional statistics
stats = []
for i, time in enumerate(ds.time.values):
    day_data = ds['NDSI'].isel(time=i)
    
    stats.append({
        'date': str(time)[:10],
        'mean': float(day_data.mean()),
        'std': float(day_data.std()),
        'min': float(day_data.min()),
        'max': float(day_data.max()),
        'snow_fraction': float((day_data > 50).sum() / day_data.count())
    })

df = pd.DataFrame(stats)
df.to_csv('daily_statistics.csv', index=False)
```

---

## Export for QGIS

### Virtual Raster (VRT)

Create a VRT for time series in QGIS:

```python
import xarray as xr
from pathlib import Path
import subprocess

# First, export individual GeoTIFFs
# (use batch export code above)

# Then create VRT
geotiffs = sorted(Path('./geotiffs').glob('snow_*.tif'))
file_list = Path('./geotiffs/files.txt')

with open(file_list, 'w') as f:
    for tif in geotiffs:
        f.write(f"{tif}\n")

# Create VRT using GDAL
subprocess.run([
    'gdalbuildvrt',
    '-separate',
    '-input_file_list', str(file_list),
    './snow_timeseries.vrt'
])

print("Created: snow_timeseries.vrt")
```

### GeoPackage

```python
import xarray as xr
import rasterio
from rasterio.transform import from_bounds

ds = xr.open_zarr('./output/snow_cover.zarr')
data = ds['NDSI'].isel(time=0).values

transform = from_bounds(
    float(ds.x.min()), float(ds.y.min()),
    float(ds.x.max()), float(ds.y.max()),
    data.shape[1], data.shape[0]
)

with rasterio.open(
    'snow_cover.gpkg',
    'w',
    driver='GPKG',
    height=data.shape[0],
    width=data.shape[1],
    count=1,
    dtype='float32',
    crs='EPSG:4326',
    transform=transform
) as dst:
    dst.write(data.astype('float32'), 1)
```

---

## Format Comparison

| Format | Use Case | Pros | Cons |
|--------|----------|------|------|
| **Zarr** | Cloud storage, large data | Fast, chunked, lazy loading | Limited GIS support |
| **GeoTIFF** | GIS software | Universal support | One file per time step |
| **NetCDF** | Scientific analysis | CF conventions, metadata | Larger files |
| **CSV** | Spreadsheets, simple analysis | Human readable | No spatial info |
| **GeoPackage** | QGIS native | Single file | Less common |
