# Output Formats

Understanding and working with SnowMapPy output data.

---

## Zarr Output Format

SnowMapPy outputs data in **Zarr format**, a modern cloud-optimized format for N-dimensional arrays.

### Why Zarr?

| Feature | Benefit |
|---------|---------|
| **Chunked storage** | Random access without reading entire file |
| **Compression** | 60%+ smaller than uncompressed |
| **Cloud-native** | Direct access from S3, GCS, Azure |
| **Lazy loading** | Works with data larger than RAM |
| **Parallel I/O** | Multiple threads can read simultaneously |

### Output Structure

```
output_name.zarr/
├── .zattrs              # Dataset metadata
├── .zgroup              # Zarr group marker
├── NDSI/
│   ├── .zarray          # Array metadata (shape, chunks, dtype)
│   ├── .zattrs          # Variable attributes
│   ├── 0.0.0            # Chunk files
│   ├── 0.0.1
│   └── ...
├── time/
│   ├── .zarray
│   └── 0
├── x/
│   ├── .zarray
│   └── 0
└── y/
    ├── .zarray
    └── 0
```

---

## Loading Output Data

### With xarray (Recommended)

```python
import xarray as xr

# Open the dataset
ds = xr.open_zarr('output/study_area_NDSI.zarr')

# View structure
print(ds)

# Access the NDSI variable
ndsi = ds['NDSI']
print(ndsi.shape)  # (time, y, x)
```

### With Dask (For Large Data)

```python
import xarray as xr
import dask

# Open with Dask chunking
ds = xr.open_zarr('output/study_area_NDSI.zarr', chunks='auto')

# Operations are lazy
mean_snow = ds['NDSI'].mean(dim='time')

# Compute when ready
result = mean_snow.compute()
```

### Direct Zarr Access

```python
import zarr

# Low-level access
store = zarr.open('output/study_area_NDSI.zarr', mode='r')
print(store.tree())
```

---

## Data Variables

### NDSI (Primary Output)

| Attribute | Value |
|-----------|-------|
| Name | NDSI |
| Units | % (0-100) |
| Dimensions | (time, y, x) |
| Data Type | float16 |
| No Data | NaN |
| Description | Gap-filled NDSI snow cover |

### Coordinates

| Coordinate | Description |
|------------|-------------|
| `time` | datetime64 timestamps |
| `x` | Longitude (degrees) |
| `y` | Latitude (degrees) |

---

## Exporting to Other Formats

### GeoTIFF (Single Time Step)

```python
import xarray as xr
import rasterio
from rasterio.transform import from_bounds

# Load data
ds = xr.open_zarr('output/study_area_NDSI.zarr')

# Select a single day
day_data = ds['NDSI'].isel(time=0).values

# Create transform
transform = from_bounds(
    float(ds.x.min()), float(ds.y.min()),
    float(ds.x.max()), float(ds.y.max()),
    day_data.shape[1], day_data.shape[0]
)

# Write GeoTIFF
with rasterio.open(
    'snow_cover_day1.tif',
    'w',
    driver='GTiff',
    height=day_data.shape[0],
    width=day_data.shape[1],
    count=1,
    dtype='float32',
    crs='EPSG:4326',
    transform=transform,
    compress='lzw'
) as dst:
    dst.write(day_data.astype('float32'), 1)
```

### GeoTIFF Stack (Multi-Band)

```python
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
import numpy as np

ds = xr.open_zarr('output/study_area_NDSI.zarr')
data = ds['NDSI'].values  # (time, y, x)

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
    count=data.shape[0],  # One band per time step
    dtype='float32',
    crs='EPSG:4326',
    transform=transform,
    compress='lzw'
) as dst:
    for i in range(data.shape[0]):
        dst.write(data[i].astype('float32'), i + 1)
```

### NetCDF

```python
import xarray as xr

# Load Zarr
ds = xr.open_zarr('output/study_area_NDSI.zarr')

# Save as NetCDF
ds.to_netcdf('snow_cover.nc', engine='netcdf4')
```

### CSV (Time Series at Point)

```python
import xarray as xr
import pandas as pd

ds = xr.open_zarr('output/study_area_NDSI.zarr')

# Extract time series at a point
lat, lon = 33.5, -7.0
ts = ds['NDSI'].sel(y=lat, x=lon, method='nearest')

# Create DataFrame
df = pd.DataFrame({
    'date': ds.time.values,
    'ndsi': ts.values
})

# Save to CSV
df.to_csv('snow_timeseries.csv', index=False)
```

---

## Metadata

### Dataset Attributes

Access processing metadata:

```python
import xarray as xr

ds = xr.open_zarr('output/study_area_NDSI.zarr')

# View all attributes
print(ds.attrs)

# Common attributes
print(f"CRS: {ds.attrs.get('crs', 'EPSG:4326')}")
print(f"Created: {ds.attrs.get('created')}")
```

### Processing Counters

The `counters` dict returned by `process_modis_ndsi_cloud` contains:

```python
result, counters = process_modis_ndsi_cloud(...)

print(counters)
# {
#     'total_pixels': 1000000,
#     'valid_pixels': 850000,
#     'interpolated_pixels': 150000,
#     'remaining_gaps': 0,
#     ...
# }
```

---

## Working with Large Outputs

### Subset by Time

```python
import xarray as xr

ds = xr.open_zarr('output/study_area_NDSI.zarr')

# Select date range
winter = ds.sel(time=slice('2020-12-01', '2021-02-28'))
```

### Subset by Region

```python
import xarray as xr

ds = xr.open_zarr('output/study_area_NDSI.zarr')

# Select bounding box
subset = ds.sel(
    x=slice(-8.0, -6.0),
    y=slice(34.0, 32.0)  # Note: y may be descending
)
```

### Compute Statistics

```python
import xarray as xr

ds = xr.open_zarr('output/study_area_NDSI.zarr')

# Temporal statistics
mean_snow = ds['NDSI'].mean(dim='time')
max_snow = ds['NDSI'].max(dim='time')
snow_days = (ds['NDSI'] > 50).sum(dim='time')

# Spatial statistics
area_mean = ds['NDSI'].mean(dim=['x', 'y'])
```

---

## Best Practices

!!! tip "Working with Large Data"
    
    1. Use **lazy loading** with `xr.open_zarr()` - don't load entire dataset
    2. **Subset before computing** - select only what you need
    3. Use **Dask** for parallel computation
    4. **Stream outputs** - process and write in chunks
