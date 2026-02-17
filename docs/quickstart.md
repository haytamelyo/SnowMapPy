# Quick Start

Get up and running with SnowMapPy in under 5 minutes.

---

## :one: Prerequisites Check

Before you begin, ensure:

1. **SnowMapPy is installed**: `pip install SnowMapPy`
2. **GEE is authenticated**: `earthengine authenticate`
3. **You have a study area shapefile** (or use our example below)

---

## :two: Your First Analysis

Here's a minimal example to process one month of snow cover data:

```python
from SnowMapPy import process_modis_ndsi_cloud

# Process snow cover data for January 2020
result, counters = process_modis_ndsi_cloud(
    project_name="your-gee-project-id",      # Your GEE project
    shapefile_path="study_area.shp",          # Your study area
    start_date="2020-01-01",                  # Start date
    end_date="2020-01-31",                    # End date
    output_path="./output"                    # Output directory
)

print(f"Successfully processed {len(result.time)} days of data!")
```

!!! info "What's happening?"
    
    1. SnowMapPy connects to Google Earth Engine
    2. Downloads MODIS Terra and Aqua snow cover data
    3. Applies quality control and sensor fusion
    4. Performs spatio-temporal gap-filling
    5. Saves the result as a Zarr dataset

---

## :three: Understanding the Output

The result is an `xarray.Dataset` with gap-filled snow cover data:

```python
# Explore the data
print(result)
```

Output:
```
<xarray.Dataset>
Dimensions:      (time: 31, y: 450, x: 380)
Coordinates:
  * time         (time) datetime64[ns] 2020-01-01 ... 2020-01-31
  * y            (y) float64 35.5 35.49 35.48 ... 31.02 31.01 31.0
  * x            (x) float64 -9.5 -9.49 -9.48 ... -5.72 -5.71 -5.7
Data variables:
    NDSI         (time, y, x) float16 ...
    ...
```

### Access the Data

```python
# Get snow cover values for a specific day
day_1 = result['NDSI'].isel(time=0)
print(f"Shape: {day_1.shape}")
print(f"Min: {day_1.min().values:.2f}, Max: {day_1.max().values:.2f}")

# Get time series at a specific location
lat, lon = 33.5, -7.0
point_ts = result['NDSI'].sel(y=lat, x=lon, method='nearest')
print(f"Time series length: {len(point_ts)}")
```

### Save to GeoTIFF

```python
import rasterio
from rasterio.transform import from_bounds

# Export a single day to GeoTIFF
data = result['NDSI'].isel(time=0).values
transform = from_bounds(
    result.x.min(), result.y.min(),
    result.x.max(), result.y.max(),
    data.shape[1], data.shape[0]
)

with rasterio.open(
    'snow_cover_day1.tif', 'w',
    driver='GTiff',
    height=data.shape[0],
    width=data.shape[1],
    count=1,
    dtype=data.dtype,
    crs='EPSG:4326',
    transform=transform
) as dst:
    dst.write(data, 1)
```

---

## :four: Visualize Results

### Static Map

```python
import matplotlib.pyplot as plt

# Plot the first day
fig, ax = plt.subplots(figsize=(10, 8))
result['NDSI'].isel(time=0).plot(
    ax=ax,
    cmap='Blues',
    vmin=0, vmax=100,
    cbar_kwargs={'label': 'NDSI (%)'}
)
ax.set_title('Snow Cover - January 1, 2020')
plt.savefig('snow_cover_map.png', dpi=150)
plt.show()
```

### Animated Time Series

```python
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

fig, ax = plt.subplots(figsize=(10, 8))

def update(frame):
    ax.clear()
    result['NDSI'].isel(time=frame).plot(
        ax=ax, cmap='Blues', vmin=0, vmax=100,
        add_colorbar=False
    )
    ax.set_title(f'Snow Cover - {result.time[frame].values}')
    return ax

anim = FuncAnimation(fig, update, frames=len(result.time), interval=200)
anim.save('snow_animation.gif', writer='pillow', fps=5)
```

---

## :five: Common Options

Customize the processing with these parameters:

```python
result, counters = process_modis_ndsi_cloud(
    project_name="your-gee-project",
    shapefile_path="study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output",
    
    # Interpolation method
    interpolation_method="nearest",     # "nearest", "linear", or "cubic"
    
    # Spatial correction using DEM
    spatial_correction_method="elevation_mean",  # or "none"
    
    # Output format
    output_dtype="float16",             # Smaller files
    compression="zstd",                 # Fast compression
    
    # Custom output name
    output_name="my_analysis"           # Creates my_analysis.zarr
)
```

---

## :six: Next Steps

Now that you've run your first analysis:

| Topic | Description |
|-------|-------------|
| [GEE Setup](gee-setup.md) | Detailed Earth Engine configuration |
| [Interpolation](user-guide/interpolation.md) | Choose the right interpolation method |
| [Spatial Correction](user-guide/spatial-correction.md) | DEM-based snow correction |
| [API Reference](api/index.md) | Full parameter documentation |
| [Examples](examples/index.md) | Real-world workflow examples |

---

## :keyboard: Command Line Interface

Prefer the command line? SnowMapPy includes a full CLI:

```bash
snowmappy process \
    --project your-gee-project \
    --shapefile study_area.shp \
    --start 2020-01-01 \
    --end 2020-12-31 \
    --output ./output
```

See [CLI Reference](cli.md) for all commands and options.
