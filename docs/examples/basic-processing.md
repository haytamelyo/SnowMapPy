# Basic Processing Example

Step-by-step guide to process one year of MODIS snow cover data.

---

## Overview

This example demonstrates the complete workflow for processing one year of snow cover data for a mountain study area.

---

## Prerequisites

```python
# Import required packages
from SnowMapPy import process_modis_ndsi_cloud
import xarray as xr
import matplotlib.pyplot as plt
```

---

## Step 1: Prepare Study Area

Create or obtain a shapefile defining your study area:

```python
# Option 1: Use existing shapefile
shapefile_path = "path/to/your/study_area.shp"

# Option 2: Create from coordinates using geopandas
import geopandas as gpd
from shapely.geometry import box

# Define bounding box (minx, miny, maxx, maxy)
bounds = box(-8.5, 31.0, -5.0, 34.5)
gdf = gpd.GeoDataFrame({'geometry': [bounds]}, crs="EPSG:4326")
gdf.to_file("study_area.shp")
shapefile_path = "study_area.shp"
```

---

## Step 2: Process Snow Cover Data

Run the main processing function:

```python
from SnowMapPy import process_modis_ndsi_cloud

# Process 2020 snow cover
result, counters = process_modis_ndsi_cloud(
    project_name="your-gee-project",
    shapefile_path=shapefile_path,
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output",
    interpolation_method="nearest",
    spatial_correction_method="elevation_mean"
)
```

Expected console output:

```
SnowMapPy v1.0.0 | MODIS Snow Cover Gap-Filling

Processing Parameters
---------------------
  Study area:          study_area.shp
  Date range:          2020-01-01 to 2020-12-31
  Output:              study_area_NDSI.zarr
  Target CRS:          EPSG:4326
  Interpolation:       nearest
  Spatial correction:  elevation_mean

→ Loading Terra data from Earth Engine...
→ Loading Aqua data from Earth Engine...
→ Loading DEM data from Earth Engine...
→ Clipping data to study area...
→ Applying spatio-temporal gap-filling algorithm...
Processing MODIS time series: 100%|██████████| 359/359 [02:34<00:00]

============================================================
  Processing complete!
============================================================
```

---

## Step 3: Explore Results

Examine the processed data:

```python
# View dataset structure
print(result)
print(f"\nDimensions: {dict(result.dims)}")
print(f"Variables: {list(result.data_vars)}")
print(f"Time range: {result.time.values[0]} to {result.time.values[-1]}")
```

Output:
```
<xarray.Dataset>
Dimensions:  (time: 366, y: 350, x: 280)
Coordinates:
  * time     (time) datetime64[ns] 2020-01-01 ... 2020-12-31
  * y        (y) float64 34.5 34.49 34.48 ... 31.02 31.01 31.0
  * x        (x) float64 -8.5 -8.49 -8.48 ... -5.02 -5.01 -5.0
Data variables:
    NDSI     (time, y, x) float16 ...

Dimensions: {'time': 366, 'y': 350, 'x': 280}
Variables: ['NDSI']
Time range: 2020-01-01T00:00:00.000000000 to 2020-12-31T00:00:00.000000000
```

---

## Step 4: Check Processing Statistics

Review gap-filling statistics:

```python
print("Processing Statistics:")
for key, value in counters.items():
    print(f"  {key}: {value:,}")
```

---

## Step 5: Visualize Results

### Single Day Map

```python
import matplotlib.pyplot as plt

# Select a winter day
winter_day = result['NDSI'].sel(time='2020-02-15', method='nearest')

# Create map
fig, ax = plt.subplots(figsize=(10, 8))
winter_day.plot(
    ax=ax,
    cmap='Blues',
    vmin=0, vmax=100,
    cbar_kwargs={'label': 'NDSI (%)'}
)
ax.set_title('Snow Cover - February 15, 2020')
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
plt.tight_layout()
plt.savefig('snow_map_winter.png', dpi=150)
plt.show()
```

### Time Series at Point

```python
# Extract time series at a location
lat, lon = 33.0, -7.0
ts = result['NDSI'].sel(y=lat, x=lon, method='nearest')

# Plot time series
fig, ax = plt.subplots(figsize=(12, 4))
ts.plot(ax=ax, linewidth=1)
ax.set_xlabel('Date')
ax.set_ylabel('NDSI (%)')
ax.set_title(f'Snow Cover Time Series at ({lat}°N, {abs(lon)}°W)')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('snow_timeseries.png', dpi=150)
plt.show()
```

### Annual Statistics

```python
# Calculate annual statistics
mean_snow = result['NDSI'].mean(dim='time')
max_snow = result['NDSI'].max(dim='time')
snow_days = (result['NDSI'] > 50).sum(dim='time')

# Create multi-panel figure
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

mean_snow.plot(ax=axes[0], cmap='Blues', cbar_kwargs={'label': '%'})
axes[0].set_title('Mean NDSI')

max_snow.plot(ax=axes[1], cmap='Blues', cbar_kwargs={'label': '%'})
axes[1].set_title('Maximum NDSI')

snow_days.plot(ax=axes[2], cmap='YlGnBu', cbar_kwargs={'label': 'days'})
axes[2].set_title('Snow Days (NDSI > 50%)')

plt.tight_layout()
plt.savefig('annual_statistics.png', dpi=150)
plt.show()
```

---

## Step 6: Save Results

The data is automatically saved to Zarr format. Reload later:

```python
import xarray as xr

# Reload from disk
ds = xr.open_zarr('./output/study_area_NDSI.zarr')

# Continue analysis...
print(ds)
```

---

## Complete Script

```python
"""
Complete example: Process one year of MODIS snow cover data
"""
from SnowMapPy import process_modis_ndsi_cloud
import xarray as xr
import matplotlib.pyplot as plt

# Configuration
PROJECT = "your-gee-project"
SHAPEFILE = "study_area.shp"
START_DATE = "2020-01-01"
END_DATE = "2020-12-31"
OUTPUT_DIR = "./output"

# Process data
print("Starting snow cover processing...")
result, counters = process_modis_ndsi_cloud(
    project_name=PROJECT,
    shapefile_path=SHAPEFILE,
    start_date=START_DATE,
    end_date=END_DATE,
    output_path=OUTPUT_DIR,
    interpolation_method="nearest",
    spatial_correction_method="elevation_mean"
)

# Print summary
print(f"\nProcessed {len(result.time)} days")
print(f"Grid size: {result.dims['y']} x {result.dims['x']}")

# Create visualization
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Winter day
result['NDSI'].sel(time='2020-02-15', method='nearest').plot(
    ax=axes[0], cmap='Blues', vmin=0, vmax=100
)
axes[0].set_title('Winter (Feb 15)')

# Summer day
result['NDSI'].sel(time='2020-07-15', method='nearest').plot(
    ax=axes[1], cmap='Blues', vmin=0, vmax=100
)
axes[1].set_title('Summer (Jul 15)')

plt.tight_layout()
plt.savefig('seasonal_comparison.png', dpi=150)
print("Created seasonal_comparison.png")
```
